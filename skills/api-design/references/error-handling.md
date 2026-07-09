# Error Handling and Validation for ASP.NET Core APIs

All API errors use RFC 9457 Problem Details (`application/problem+json`) via ASP.NET Core's built-in `ProblemDetails` / `ValidationProblemDetails` types. Never invent a custom error envelope — clients, gateways, and tooling already understand ProblemDetails, and ASP.NET Core produces it for free.

## Baseline Setup (Every API Project)

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddProblemDetails(options =>
{
    // Enrich every problem response with correlation info
    options.CustomizeProblemDetails = context =>
    {
        context.ProblemDetails.Instance =
            $"{context.HttpContext.Request.Method} {context.HttpContext.Request.Path}";
        context.ProblemDetails.Extensions["traceId"] =
            context.HttpContext.TraceIdentifier;
    };
});

builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

var app = builder.Build();

app.UseExceptionHandler();   // converts unhandled exceptions to ProblemDetails
app.UseStatusCodePages();    // adds ProblemDetails bodies to bare 404/405/415 responses
```

With this in place:
- Unhandled exceptions → `500` ProblemDetails (stack traces only shown in Development).
- Routes that don't exist, wrong methods, unsupported media types → `404`/`405`/`415` with a ProblemDetails body instead of an empty response.

## Global Exception Handler (IExceptionHandler, .NET 8+)

One handler maps domain exceptions to status codes. Endpoints never contain try/catch for business errors:

```csharp
public sealed class GlobalExceptionHandler(
    ILogger<GlobalExceptionHandler> logger,
    IProblemDetailsService problemDetailsService) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        var (status, title) = exception switch
        {
            EntityNotFoundException => (StatusCodes.Status404NotFound, "Resource not found."),
            DuplicateEntityException => (StatusCodes.Status409Conflict, "Resource already exists."),
            DomainRuleException e    => (StatusCodes.Status422UnprocessableEntity, e.Message),
            _                        => (StatusCodes.Status500InternalServerError, "An unexpected error occurred."),
        };

        if (status == StatusCodes.Status500InternalServerError)
        {
            logger.LogError(exception, "Unhandled exception for {Path}", httpContext.Request.Path);
        }

        httpContext.Response.StatusCode = status;
        return await problemDetailsService.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = httpContext,
            ProblemDetails = { Status = status, Title = title },
            Exception = exception,
        });
    }
}
```

Rules:
- Log 5xx at `Error` with the exception; do not log expected 4xx as errors (noise).
- The 500 message is generic on purpose — never echo `exception.Message` for unexpected exceptions (may contain connection strings, SQL, file paths).
- Prefer returning `TypedResults.NotFound()` etc. directly from handlers when the condition is local; use exceptions for violations raised deep in the domain layer.

## Expected Errors: Return, Don't Throw

For conditions the endpoint itself checks, return typed results with ProblemDetails:

```csharp
private static async Task<Results<Ok<OrderResponse>, NotFound, UnprocessableEntity<ProblemDetails>>>
    CancelOrder(Guid id, AppDbContext db, CancellationToken ct)
{
    var order = await db.Orders.FindAsync([id], ct);
    if (order is null)
        return TypedResults.NotFound();

    if (order.Status is OrderStatus.Shipped or OrderStatus.Delivered)
    {
        return TypedResults.UnprocessableEntity(new ProblemDetails
        {
            Title = "Order cannot be cancelled.",
            Detail = $"Orders in status '{order.Status}' cannot be cancelled.",
            Status = StatusCodes.Status422UnprocessableEntity,
        });
    }

    order.Status = OrderStatus.Cancelled;
    await db.SaveChangesAsync(ct);
    return TypedResults.Ok(new OrderResponse(order.Id, order.Total, order.Status));
}
```

## Validation

### .NET 10: Built-in Minimal API Validation

.NET 10 validates data annotations on minimal API parameters automatically:

```csharp
builder.Services.AddValidation();   // Microsoft.Extensions.Validation
```

```csharp
public sealed record CreateUserRequest(
    [property: Required, EmailAddress] string Email,
    [property: Required, StringLength(100, MinimumLength = 1)] string Name,
    [property: Range(0, 150)] int? Age);
```

Invalid requests short-circuit with `400` `ValidationProblemDetails` before the handler runs:

```json
{
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "Email": ["The Email field is not a valid e-mail address."],
    "Name": ["The Name field is required."]
  }
}
```

Opt out per endpoint with `.DisableValidation()` if needed.

### .NET 8/9 or Complex Rules: FluentValidation via Endpoint Filter

For cross-field rules, async checks, or when targeting .NET 8/9, use FluentValidation (`dotnet add package FluentValidation.DependencyInjectionExtensions`):

```csharp
public sealed class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Email).NotEmpty().EmailAddress();
        RuleFor(x => x.Name).NotEmpty().MaximumLength(100);
    }
}
```

Reusable endpoint filter that returns `ValidationProblemDetails`:

```csharp
public sealed class ValidationFilter<T> : IEndpointFilter where T : class
{
    public async ValueTask<object?> InvokeAsync(
        EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var validator = context.HttpContext.RequestServices.GetService<IValidator<T>>();
        var argument = context.Arguments.OfType<T>().FirstOrDefault();

        if (validator is not null && argument is not null)
        {
            var result = await validator.ValidateAsync(argument, context.HttpContext.RequestAborted);
            if (!result.IsValid)
                return TypedResults.ValidationProblem(result.ToDictionary());
        }

        return await next(context);
    }
}
```

Registration:

```csharp
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserRequestValidator>();

users.MapPost("/", CreateUser)
    .AddEndpointFilter<ValidationFilter<CreateUserRequest>>();
```

### Controllers

`[ApiController]` already returns `ValidationProblemDetails` for invalid `ModelState` automatically — do not re-implement it. Keep that default; never set `SuppressModelStateInvalidFilter = true` without a reason.

## Status Code Decision Table for Errors

| Situation | Status | Body |
|-----------|--------|------|
| Malformed JSON, missing required field, bad format | 400 | `ValidationProblemDetails` with `errors` dictionary |
| No/invalid token | 401 | (auth middleware handles it; include `WWW-Authenticate`) |
| Valid token, insufficient role | 403 | ProblemDetails |
| Resource missing, or owned by someone else | 404 | ProblemDetails (don't reveal existence of others' resources) |
| Duplicate unique key, optimistic concurrency failure | 409 | ProblemDetails naming the conflict |
| Well-formed but violates a business rule | 422 | ProblemDetails with `detail` explaining the rule |
| Rate limit hit | 429 | ProblemDetails + `Retry-After` header |
| Anything unexpected | 500 | Generic ProblemDetails — no exception details |

## Anti-Patterns

```csharp
// BAD: custom error envelope — breaks ProblemDetails tooling
return Results.Json(new { success = false, error = "Not found" }, statusCode: 404);

// BAD: try/catch in every endpoint returning 500 manually
// GOOD: let it bubble to the IExceptionHandler

// BAD: exposing exception details
return Results.Problem(detail: ex.ToString());   // leaks stack trace/SQL

// BAD: 200 with an error flag in the body
```
