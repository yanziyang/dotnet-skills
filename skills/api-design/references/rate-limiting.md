# Rate Limiting for ASP.NET Core APIs

ASP.NET Core has built-in rate limiting middleware (`Microsoft.AspNetCore.RateLimiting`, .NET 7+). No third-party package needed for single-instance limits.

## Baseline Setup

```csharp
using System.Threading.RateLimiting;

builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;

    // ProblemDetails body + Retry-After header on rejection
    options.OnRejected = async (context, cancellationToken) =>
    {
        var response = context.HttpContext.Response;

        if (context.Lease.TryGetMetadata(MetadataName.RetryAfter, out var retryAfter))
        {
            response.Headers.RetryAfter =
                ((int)retryAfter.TotalSeconds).ToString(CultureInfo.InvariantCulture);
        }

        response.ContentType = "application/problem+json";
        await response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = StatusCodes.Status429TooManyRequests,
            Title = "Too many requests.",
            Detail = "Rate limit exceeded. Retry after the interval in the Retry-After header.",
        }, cancellationToken);
    };

    // Named policies — attach per endpoint/group
    options.AddFixedWindowLimiter("fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 100;
        limiterOptions.Window = TimeSpan.FromMinutes(1);
        limiterOptions.QueueLimit = 0;              // reject immediately, don't queue API calls
    });
});

var app = builder.Build();
app.UseRateLimiter();   // after UseExceptionHandler, before UseAuthentication is fine for global IP limits;
                        // place after UseAuthentication if partition keys need the authenticated user
```

Attach to endpoints or groups:

```csharp
app.MapGroup("/api/v1").RequireRateLimiting("fixed");
app.MapGet("/api/v1/health", () => Results.Ok()).DisableRateLimiting();
```

## Choosing an Algorithm

| Limiter | Behavior | Use For |
|---------|----------|---------|
| Fixed window | N requests per clock window; resets at boundary | Simple default; per-user API quotas |
| Sliding window | Window divided into segments; smooths the boundary-burst problem | Public APIs where 2× bursts at window edges matter |
| Token bucket | Refills at a steady rate; allows short bursts up to bucket size | Traffic that is naturally bursty (mobile sync, batch clients) |
| Concurrency | Caps in-flight requests, not rate | Protecting expensive endpoints (reports, exports, LLM calls) |

```csharp
options.AddSlidingWindowLimiter("sliding", o =>
{
    o.PermitLimit = 100;
    o.Window = TimeSpan.FromMinutes(1);
    o.SegmentsPerWindow = 6;              // 10-second segments
    o.QueueLimit = 0;
});

options.AddTokenBucketLimiter("bursty", o =>
{
    o.TokenLimit = 100;                   // max burst
    o.ReplenishmentPeriod = TimeSpan.FromSeconds(10);
    o.TokensPerPeriod = 20;               // steady-state: 120/min
    o.QueueLimit = 0;
});

options.AddConcurrencyLimiter("expensive", o =>
{
    o.PermitLimit = 10;                   // 10 in flight
    o.QueueLimit = 20;                    // queue up to 20 more
    o.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
});
```

Keep `QueueLimit = 0` for user-facing API endpoints — a queued request that waits 30 seconds is worse than a fast 429 the client can retry.

## Partitioning: Per-User and Per-IP Limits

A single shared limiter lets one client starve everyone. Partition by authenticated user, falling back to IP for anonymous traffic:

```csharp
options.AddPolicy("per-user", httpContext =>
{
    var userId = httpContext.User.FindFirstValue(ClaimTypes.NameIdentifier);

    if (userId is not null)
    {
        return RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: $"user:{userId}",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 100,
                Window = TimeSpan.FromMinutes(1),
            });
    }

    return RateLimitPartition.GetFixedWindowLimiter(
        partitionKey: $"ip:{httpContext.Connection.RemoteIpAddress}",
        factory: _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 30,                 // stricter for anonymous
            Window = TimeSpan.FromMinutes(1),
        });
});
```

Behind a load balancer or reverse proxy, `RemoteIpAddress` is the proxy — configure forwarded headers first (`app.UseForwardedHeaders(...)` with `KnownProxies`/`KnownNetworks`) or every client shares one partition.

## Tiered Limits (API Plans)

Resolve the tier from claims or an API-key lookup and vary the partition options:

```csharp
options.AddPolicy("tiered", httpContext =>
{
    var tier = httpContext.User.FindFirstValue("plan") ?? "anonymous";
    var key = httpContext.User.FindFirstValue(ClaimTypes.NameIdentifier)
              ?? httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";

    var permitLimit = tier switch
    {
        "premium"  => 1000,
        "standard" => 100,
        _          => 30,
    };

    return RateLimitPartition.GetFixedWindowLimiter($"{tier}:{key}", _ =>
        new FixedWindowRateLimiterOptions
        {
            PermitLimit = permitLimit,
            Window = TimeSpan.FromMinutes(1),
        });
});
```

Suggested tiers:

| Tier | Limit | Partition key | Use Case |
|------|-------|---------------|----------|
| Anonymous | 30/min | IP | Public endpoints |
| Authenticated | 100/min | User id | Standard API access |
| Premium | 1000/min | API key | Paid plans |
| Internal | 10000/min | Service name | Service-to-service |

## Communicating Limits to Clients

On 429, always send `Retry-After` (the `OnRejected` handler above does this). To also advertise quota on successful responses, emit the IETF draft standard headers (`RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`) — the built-in middleware doesn't emit these automatically, so either add them in the partition policy via a small middleware that queries limiter statistics (`GetStatistics()`), or document limits statically in your API docs. Many public APIs still use the legacy `X-RateLimit-*` names; pick one convention and keep it consistent.

Document client expectations: honor `Retry-After`, use exponential backoff with jitter, treat 429 as retryable and 4xx as not.

## Multi-Instance Deployments

The built-in limiter is in-memory and per-instance: with 3 replicas behind a load balancer, a "100/min" policy allows up to ~300/min globally. Options:

- Accept it — set per-instance limits to `global limit / replica count` (approximation; fine for abuse protection).
- Enforce at the gateway instead — YARP, Azure API Management, AWS API Gateway, Cloudflare, or nginx handle distributed limits natively. Prefer this for hard billing quotas.
- Distributed limiter backed by Redis (e.g., the `RedisRateLimiting` community package) when the app must enforce exact global limits itself.

Rule of thumb: in-app limiting for abuse protection and fairness; gateway limiting for billed quotas.
