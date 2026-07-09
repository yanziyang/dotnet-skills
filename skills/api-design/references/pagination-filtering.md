# Pagination, Filtering, Sorting, and Search for ASP.NET Core APIs

Every list endpoint must be paginated from day one — adding pagination later is a breaking change. Never return a bare JSON array; always wrap in a paged envelope so metadata can be added without breaking clients.

## Shared Types

```csharp
public sealed record PagedResponse<T>(
    IReadOnlyList<T> Items,
    int Page,
    int PageSize,
    int TotalCount)
{
    public int TotalPages => (int)Math.Ceiling(TotalCount / (double)PageSize);
}

public sealed record CursorPagedResponse<T>(
    IReadOnlyList<T> Items,
    string? NextCursor,
    bool HasMore);
```

## Choosing a Strategy

| Use Case | Strategy |
|----------|----------|
| Admin dashboards, small datasets (<100K rows), "jump to page N" | Offset |
| Infinite scroll, feeds, exports, large or hot tables | Cursor (keyset) |
| Public APIs | Cursor by default |
| Search results UIs | Offset (users expect page numbers) |

Offset degrades linearly (`OFFSET 100000` scans 100K rows) and skips/duplicates rows when items are inserted between requests. Keyset pagination is O(index seek) and stable under concurrent writes.

## Offset Pagination (EF Core)

Bind query parameters via a record with `[AsParameters]`, and always cap the page size — an uncapped `pageSize=100000` is a self-inflicted DoS:

```csharp
public sealed record PagingQuery(int Page = 1, int PageSize = 20)
{
    public const int MaxPageSize = 100;
    public int ClampedPage => Math.Max(1, Page);
    public int ClampedPageSize => Math.Clamp(PageSize, 1, MaxPageSize);
}

private static async Task<Ok<PagedResponse<UserResponse>>> GetUsers(
    [AsParameters] PagingQuery paging, AppDbContext db, CancellationToken ct)
{
    var query = db.Users.OrderByDescending(u => u.CreatedAt).ThenBy(u => u.Id);

    var totalCount = await query.CountAsync(ct);
    var items = await query
        .Skip((paging.ClampedPage - 1) * paging.ClampedPageSize)
        .Take(paging.ClampedPageSize)
        .Select(u => new UserResponse(u.Id, u.Email, u.Name, u.CreatedAt))
        .ToListAsync(ct);

    return TypedResults.Ok(new PagedResponse<UserResponse>(
        items, paging.ClampedPage, paging.ClampedPageSize, totalCount));
}
```

Always include a unique tiebreaker (`ThenBy(u => u.Id)`) — ordering by a non-unique column alone makes page boundaries non-deterministic.

## Cursor (Keyset) Pagination (EF Core)

The cursor encodes the sort-key values of the last item. Fetch `limit + 1` rows to detect whether more exist:

```csharp
private static async Task<Ok<CursorPagedResponse<UserResponse>>> GetUsersFeed(
    string? cursor, int limit, AppDbContext db, CancellationToken ct)
{
    limit = Math.Clamp(limit, 1, 100);

    IQueryable<User> query = db.Users.OrderBy(u => u.Id);

    if (Cursor.TryDecode(cursor, out Guid afterId))
        query = query.Where(u => u.Id > afterId);

    var rows = await query
        .Take(limit + 1)                             // one extra to detect HasMore
        .Select(u => new UserResponse(u.Id, u.Email, u.Name, u.CreatedAt))
        .ToListAsync(ct);

    var hasMore = rows.Count > limit;
    var items = hasMore ? rows[..limit] : rows;
    var nextCursor = hasMore ? Cursor.Encode(items[^1].Id) : null;

    return TypedResults.Ok(new CursorPagedResponse<UserResponse>(items, nextCursor, hasMore));
}
```

Opaque cursor helper (Base64Url so clients can't depend on internals):

```csharp
public static class Cursor
{
    public static string Encode(Guid id) =>
        Base64Url.EncodeToString(id.ToByteArray());

    public static bool TryDecode(string? cursor, out Guid id)
    {
        id = default;
        if (string.IsNullOrEmpty(cursor)) return false;
        try
        {
            id = new Guid(Base64Url.DecodeFromChars(cursor));
            return true;
        }
        catch (FormatException) { return false; }
    }
}
```

Notes:
- Sorting by a non-unique column (e.g., `CreatedAt` descending) requires a composite cursor: `WHERE (CreatedAt, Id) < (@createdAt, @id)` — in EF Core: `.Where(u => u.CreatedAt < c.CreatedAt || (u.CreatedAt == c.CreatedAt && u.Id < c.Id))`. EF Core 10 translates tuple comparisons efficiently on providers that support row values.
- An invalid cursor should return `400`, not `500` — hence `TryDecode`.
- Cursor responses usually omit `totalCount` (a full COUNT defeats the purpose).

## Filtering

Bind filters as nullable properties on an `[AsParameters]` record; apply conditionally:

```csharp
public sealed record OrderFilter(
    OrderStatus? Status,
    Guid? CustomerId,
    decimal? MinTotal,
    decimal? MaxTotal,
    DateTimeOffset? CreatedAfter);

private static IQueryable<Order> ApplyFilter(IQueryable<Order> query, OrderFilter f)
{
    if (f.Status is not null)       query = query.Where(o => o.Status == f.Status);
    if (f.CustomerId is not null)   query = query.Where(o => o.CustomerId == f.CustomerId);
    if (f.MinTotal is not null)     query = query.Where(o => o.Total >= f.MinTotal);
    if (f.MaxTotal is not null)     query = query.Where(o => o.Total <= f.MaxTotal);
    if (f.CreatedAfter is not null) query = query.Where(o => o.CreatedAt > f.CreatedAfter);
    return query;
}
```

URL conventions:

```
# Simple equality
GET /api/v1/orders?status=active&customerId=0198c5f3-...

# Ranges: use explicit min/max parameter names (binds cleanly, self-documenting)
GET /api/v1/orders?minTotal=10&maxTotal=100
GET /api/v1/orders?createdAfter=2026-01-01T00:00:00Z

# Multiple values: repeat the parameter (binds to arrays natively)
GET /api/v1/products?category=electronics&category=clothing
```

Repeated parameters bind to `string[]`/`int[]` automatically in ASP.NET Core — prefer that over comma-splitting.

## Sorting

Accept `sort=field` or `sort=-field` (descending). Whitelist sortable fields explicitly — never build `OrderBy` from raw user input (property-name injection, unindexed sorts):

```csharp
private static IOrderedQueryable<Product> ApplySort(IQueryable<Product> query, string? sort)
{
    var descending = sort?.StartsWith('-') == true;
    var field = descending ? sort![1..] : sort;

    var ordered = (field?.ToLowerInvariant()) switch
    {
        "price"     => descending ? query.OrderByDescending(p => p.Price)     : query.OrderBy(p => p.Price),
        "name"      => descending ? query.OrderByDescending(p => p.Name)      : query.OrderBy(p => p.Name),
        "createdat" => descending ? query.OrderByDescending(p => p.CreatedAt) : query.OrderBy(p => p.CreatedAt),
        _           => query.OrderByDescending(p => p.CreatedAt),   // documented default
    };

    return ordered.ThenBy(p => p.Id);   // stable tiebreaker, always
}
```

Return `400` ProblemDetails for an unrecognized sort field on public APIs (instead of silently defaulting) so client typos surface early.

## Search

```
GET /api/v1/products?q=wireless+headphones
```

```csharp
if (!string.IsNullOrWhiteSpace(q))
{
    var term = $"%{q.Trim()}%";
    query = query.Where(p =>
        EF.Functions.Like(p.Name, term) || EF.Functions.Like(p.Description, term));
}
```

`LIKE '%term%'` cannot use an index — fine for small tables. Beyond that, use the database's full-text search (SQL Server FTS via `EF.Functions.Contains`, PostgreSQL tsvector via `EF.Functions.ToTsVector`) or a dedicated search service. Do not interpolate the raw query into SQL.

## Rules Summary

- Every list endpoint: paginated, capped page size, stable ordering with unique tiebreaker.
- Project to DTOs inside the query (`Select` before `ToListAsync`) so SQL fetches only needed columns.
- Filters are typed nullable parameters — no dynamic LINQ, no expression parsing from strings.
- Sort fields are whitelisted via `switch`.
- Cursors are opaque (Base64Url) and invalid cursors return 400.
