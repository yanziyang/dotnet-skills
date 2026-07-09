# API Versioning for ASP.NET Core

Use the `Asp.Versioning` packages (the maintained successor to Microsoft.AspNetCore.Mvc.Versioning):

```
dotnet add package Asp.Versioning.Http          # Minimal APIs
dotnet add package Asp.Versioning.Mvc           # Controllers (instead of .Http)
dotnet add package Asp.Versioning.Mvc.ApiExplorer   # only if generating per-version OpenAPI docs
```

## Strategy Rules

1. Start every API with `/api/v1/` from day one — retrofitting a version prefix is a breaking change for all clients.
2. URL path versioning (`/api/v1/users`) is the default choice: explicit, easy to route, curl-able, cacheable. Use header/media-type versioning only when a platform team mandates stable URLs.
3. Maintain at most 2 active versions (current + previous). Every extra live version multiplies test and support cost.
4. **Non-breaking — do NOT bump the version:** adding response fields, adding optional query parameters, adding new endpoints, relaxing validation.
5. **Breaking — new version required:** removing/renaming fields, changing field types or semantics, changing URL structure, tightening validation, changing auth.
6. Clients must ignore unknown response fields (document this in your API docs); that's what makes rule 4 safe.

## Setup (Minimal APIs)

```csharp
builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;                       // adds api-supported-versions header
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
});
```

Define a version set and map endpoints per version:

```csharp
var versionSet = app.NewApiVersionSet()
    .HasApiVersion(new ApiVersion(1, 0))
    .HasApiVersion(new ApiVersion(2, 0))
    .ReportApiVersions()
    .Build();

var users = app.MapGroup("/api/v{version:apiVersion}/users")
    .WithApiVersionSet(versionSet);

// v1 and v2 both serve this endpoint (unchanged between versions)
users.MapGet("/{id:guid}", GetUserV1)
    .MapToApiVersion(1, 0);

// v2 has a different response shape
users.MapGet("/{id:guid}", GetUserV2)
    .MapToApiVersion(2, 0);
```

Requesting a version that isn't in the set returns `400` with error code `UnsupportedApiVersion` automatically.

## Setup (Controllers)

```csharp
builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
    options.ApiVersionReader = new UrlSegmentApiVersionReader();
}).AddMvc();
```

```csharp
[ApiController]
[ApiVersion(1.0)]
[ApiVersion(2.0)]
[Route("api/v{version:apiVersion}/users")]
public sealed class UsersController : ControllerBase
{
    [HttpGet("{id:guid}")]
    [MapToApiVersion(1.0)]
    public async Task<ActionResult<UserResponseV1>> GetV1(Guid id, CancellationToken ct) { ... }

    [HttpGet("{id:guid}")]
    [MapToApiVersion(2.0)]
    public async Task<ActionResult<UserResponseV2>> GetV2(Guid id, CancellationToken ct) { ... }
}
```

## Versioning DTOs, Not the Whole World

Only fork what changed. Keep one service/domain layer; create `V2` request/response records and map both versions onto the same domain logic:

```csharp
public sealed record UserResponseV1(Guid Id, string Email, string Name, DateTimeOffset CreatedAt);

// v2 splits Name into First/Last — a breaking change
public sealed record UserResponseV2(Guid Id, string Email, string FirstName, string LastName, DateTimeOffset CreatedAt);
```

Do not duplicate the database layer or domain services per version. If two versions need different domain behavior (not just shape), that's a sign the change belongs behind a feature flag or a new resource, not a version bump.

## Deprecation and Sunset

Mark the old version deprecated as soon as its replacement ships:

```csharp
var versionSet = app.NewApiVersionSet()
    .HasDeprecatedApiVersion(new ApiVersion(1, 0))
    .HasApiVersion(new ApiVersion(2, 0))
    .ReportApiVersions()
    .Build();
```

Deprecated versions are reported in the `api-deprecated-versions` response header.

Deprecation timeline for public APIs:

1. **Announce** — changelog, email, and response headers. Give 6+ months for public APIs, 1–2 release cycles for internal ones.
2. **Advertise sunset date** — add a `Sunset` header (RFC 8594) on all v1 responses:
   ```csharp
   var v1 = app.MapGroup("/api/v1")
       .AddEndpointFilter(async (context, next) =>
       {
           var result = await next(context);
           context.HttpContext.Response.Headers["Sunset"] = "Sat, 01 Jan 2027 00:00:00 GMT";
           context.HttpContext.Response.Headers["Link"] =
               "<https://docs.example.com/migrate-v2>; rel=\"sunset\"";
           return result;
       });
   ```
   (Asp.Versioning can also do this declaratively via `options.Policies.Sunset(...)` in `AddApiVersioning`.)
3. **Monitor** — track v1 traffic by client; contact remaining heavy users before the date.
4. **After sunset** — return `410 Gone` with a ProblemDetails body pointing at the migration guide. Do not silently 404.

## Per-Version OpenAPI Documents

With the built-in OpenAPI generator (.NET 9+), register one document per version:

```csharp
builder.Services.AddOpenApi("v1");
builder.Services.AddOpenApi("v2");

app.MapOpenApi();   // serves /openapi/v1.json and /openapi/v2.json
```

Tag endpoints with their group name so they land in the right document:

```csharp
users.MapGet("/{id:guid}", GetUserV1).MapToApiVersion(1, 0).WithGroupName("v1");
users.MapGet("/{id:guid}", GetUserV2).MapToApiVersion(2, 0).WithGroupName("v2");
```
