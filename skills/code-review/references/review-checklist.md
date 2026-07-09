# .NET Review Checklist

The defect catalog for the review pass. Each entry has: **Detect** (what to look for, with a grep pattern where one works), **Why** (the concrete failure), **Fix** (the correct idiom), and where needed **Not a finding when** — the counter-signal that makes the pattern legitimate. Severities shown are defaults; the SKILL.md rubric always wins.

Grep patterns are regexes for `rg` / the Grep tool, run over the changed files only.

## Contents

1. [Async & threading](#1-async--threading)
2. [Data access (EF Core)](#2-data-access-ef-core)
3. [Security](#3-security)
4. [Correctness](#4-correctness)
5. [Resources & lifetimes](#5-resources--lifetimes)
6. [API contract (ASP.NET Core)](#6-api-contract-aspnet-core)
7. [Performance](#7-performance)
8. [Tests](#8-tests)

---

## 1. Async & threading

### 1.1 `async void` — Blocker

**Detect:** `async\s+void` — anything that isn't a UI event handler.
**Why:** An exception thrown in an `async void` method can't be caught by the caller and crashes the process. The caller also can't await completion, so work silently races shutdown.
**Fix:** Return `Task`. If an event-handler signature forces `void`, wrap the body in `try/catch` and log.

```csharp
// BAD — exception here kills the process
public async void ProcessUpload(Stream s) { await store.SaveAsync(s); }

// GOOD
public async Task ProcessUploadAsync(Stream s) { await store.SaveAsync(s); }
```

### 1.2 Sync-over-async — Warning (Blocker if it can deadlock)

**Detect:** `\.Result\b`, `\.Wait\(\)`, `GetAwaiter\(\)\.GetResult\(\)` on a `Task`.
**Why:** On ASP.NET Core there's no sync context, so it won't classically deadlock — but each blocked call pins a thread-pool thread. Under load this is thread-pool starvation: requests queue, latency spikes, health checks time out. In code with a sync context (UI, some test hosts) it deadlocks outright.
**Fix:** Make the calling chain async end to end.
**Not a finding when:** `Main` in a console app that can't be `async Task Main`, or a truly-completed task (e.g. after `Task.WhenAll` was awaited).

### 1.3 Fire-and-forget task — Warning

**Detect:** A call returning `Task` whose result is discarded: `_ = SomethingAsync(`, or a bare `SomethingAsync();` statement (the compiler warns CS4014 — check new suppressions too: `#pragma warning disable CS4014`).
**Why:** Exceptions in the forgotten task vanish; the work races app shutdown and may never complete.
**Fix:** Await it. For genuine background work in ASP.NET Core, queue to a hosted service (`IHostedService` / channel-based queue), which survives the request and observes exceptions.

### 1.4 Missing `CancellationToken` propagation — Warning

**Detect:** An endpoint/handler that receives (or could receive) a `CancellationToken` but calls async APIs without passing one: `Async\([^)]*\)\s*;` on EF/HTTP/stream calls where an overload takes a token.
**Why:** When the client disconnects, the query/IO keeps running to completion — wasted DB and CPU time that compounds under load, and long-running work that can't be shut down cleanly.
**Fix:** Accept `CancellationToken ct` (ASP.NET Core binds it automatically in endpoints) and pass it all the way down.
**Not a finding when:** the operation must not be cancelled mid-flight (e.g. the final `SaveChangesAsync` of a payment) — but then the *rest* of the chain should still take the token.

### 1.5 `DbContext` (or other non-thread-safe object) shared across concurrent tasks — Blocker

**Detect:** `Task.WhenAll(` / `Parallel.` / unawaited tasks where the lambdas touch the same injected `DbContext`, `HttpContext`, or other scoped service.
**Why:** `DbContext` is not thread-safe. Concurrent use throws `InvalidOperationException` ("a second operation was started…") intermittently — the worst kind of bug: passes locally, fails under load.
**Fix:** Sequential awaits, or one `IDbContextFactory<T>`-created context per task.

### 1.6 `await` inside `lock` / async under a `lock` — Warning

**Detect:** `lock\s*\(` in a method that is `async`. (`await` inside `lock` won't compile, so what ships is either blocking calls inside the lock or a lock that guards less than the author thinks.)
**Why:** Blocking inside a lock on the request path serializes all requests through it; splitting the critical section around the await leaves a race.
**Fix:** `SemaphoreSlim(1, 1)` with `await sem.WaitAsync(ct); try { … } finally { sem.Release(); }`.

### 1.7 Async lambda where a delegate returns `void` — Warning

**Detect:** `async` lambdas passed to `List.ForEach`, `Task.Run(() => …)` without await of the inner task, event subscriptions, `Select` without a following `Task.WhenAll`.
**Why:** `List.ForEach(async x => …)` compiles to `async void` per element — nothing awaits, exceptions vanish. `items.Select(async x => …)` produces `IEnumerable<Task>` that nobody awaited.
**Fix:** `foreach` + `await`, or `await Task.WhenAll(items.Select(x => DoAsync(x)))` when parallelism is intended (and safe — see 1.5).

---

## 2. Data access (EF Core)

### 2.1 Query in a loop (N+1) — Warning

**Detect:** `foreach`/`for` whose body contains `await …context\.` or a repository call that runs a query; also lazy-loading marker `virtual` navigation properties combined with iteration over a parent list.
**Why:** One query per element. 200 orders → 201 round-trips; the page that was fast in the demo times out with production data.
**Fix:** One query with `Include`, or better a projection (`Select`) that fetches exactly what the loop needs.

```csharp
// BAD — one query per order
foreach (var order in orders)
    order.Customer = await db.Customers.FindAsync(order.CustomerId);

// GOOD — one query
var orders = await db.Orders.Include(o => o.Customer).ToListAsync(ct);
```

### 2.2 Interpolated raw SQL — Blocker

**Detect:** `FromSqlRaw\(\$"`, `ExecuteSqlRaw\(\$"`, `SqlCommand` / Dapper `Query` with `$"` or string concatenation containing a variable.
**Why:** SQL injection. The `Raw` APIs treat the string as SQL text; interpolated user input becomes SQL.
**Fix:** `FromSql($"…{value}…")` / `FromSqlInterpolated` (these parameterize the interpolation holes), or explicit `DbParameter`s / Dapper anonymous-object parameters.
**Not a finding when:** the interpolated value is provably not user-influenced (e.g. `nameof(Column)`, a constant) — say so and drop it.

### 2.3 Client-side evaluation / premature materialization — Warning

**Detect:** `.ToList()` / `.ToArray()` / `.AsEnumerable()` followed by `.Where(`, `.OrderBy(`, `.Select(` on what was an EF query; also calling a local C# method inside a `Where` on `IQueryable`.
**Why:** The whole table crosses the wire, then gets filtered in memory. Correct results, quietly catastrophic at scale.
**Fix:** Keep the chain on `IQueryable` until the terminal `ToListAsync`/`FirstOrDefaultAsync`. Move untranslatable logic into translatable expressions or do it after a narrow projection.

### 2.4 `SaveChanges` in a loop — Warning

**Detect:** `SaveChanges(A|sync)?\(` inside a loop body.
**Why:** One transaction + round-trip per iteration. 1,000 inserts become 1,000 transactions.
**Fix:** Mutate/add inside the loop, call `SaveChangesAsync(ct)` once after.
**Not a finding when:** each iteration is deliberately its own unit of work (e.g. resumable batch processing that records progress per item).

### 2.5 Deferred query escaping its context — Blocker

**Detect:** A method returning `IQueryable<T>` or a LINQ-deferred `IEnumerable<T>` built from a `DbContext` that is disposed when the method returns (context from `using`, or returning from a scope the caller outlives).
**Why:** The query executes on first enumeration — after disposal → `ObjectDisposedException`, or much later than the author thinks.
**Fix:** Materialize (`ToListAsync`) before the context's scope ends, or align lifetimes.

### 2.6 Missing `AsNoTracking` on a read-only path — Suggestion

**Detect:** Queries whose results are only mapped/returned (never mutated + saved) without `.AsNoTracking()`.
**Why:** Change-tracking overhead (snapshots per entity) bought for nothing.
**Fix:** `.AsNoTracking()`, or a `Select` projection to a DTO (projections are never tracked — then this finding disappears entirely).

---

## 3. Security

### 3.1 Missing authorization on an endpoint — Blocker

**Detect:** New/changed controllers or minimal-API endpoints without `[Authorize]` / `.RequireAuthorization()`, in an app that uses auth elsewhere. Also `[AllowAnonymous]` added in the diff.
**Why:** The endpoint is publicly reachable. Anything mutating or returning per-user data is exposed.
**Not a finding when:** a global fallback policy covers it (check `Program.cs` for `FallbackPolicy` / `RequireAuthorization()` on a group), or the endpoint is genuinely public (health, login). Verify before reporting — this one is embarrassing to get wrong in both directions.

### 3.2 Missing ownership check (IDOR) — Blocker

**Detect:** An authorized endpoint that loads an entity purely by id from the route (`FindAsync(id)`, `FirstOrDefaultAsync(x => x.Id == id)`) and returns or mutates it, where the entity belongs to a user/tenant.
**Why:** Any authenticated user can read or modify any other user's data by iterating ids.
**Fix:** Filter by the caller's identity: `.FirstOrDefaultAsync(x => x.Id == id && x.OwnerId == userId, ct)` — and return 404 (not 403) so ids don't leak existence.

### 3.3 Over-posting / mass assignment — Blocker

**Detect:** An entity type (a `DbSet` type) used directly as a request-body parameter, or `db.Entry(entity).CurrentValues.SetValues(request)` / full-entity `Update(request)` from a client payload.
**Why:** The client controls every bound property — `IsAdmin`, `Price`, `OwnerId`.
**Fix:** A request DTO with exactly the writable fields, mapped explicitly onto the loaded entity.

### 3.4 Path traversal — Blocker

**Detect:** `Path.Combine(` where any argument comes from user input (route/query/form/file name), used for read/write/delete.
**Why:** `Path.Combine(root, "..\\..\\secrets.json")` escapes the root; an absolute path in the second argument *replaces* the root entirely.
**Fix:** Resolve then verify: `var full = Path.GetFullPath(Path.Combine(root, name)); if (!full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal)) return Results.BadRequest();`

### 3.5 Secrets in code or committed config — Blocker

**Detect:** Connection strings with passwords, API keys, tokens in `.cs`, `appsettings*.json`, or docker-compose in the diff. Pattern: `(password|pwd|apikey|api_key|secret|token)\s*[=:]\s*['"][^'"]{8,}`.
**Why:** In git history forever; rotating is the only remedy once pushed.
**Fix:** User-secrets (dev), environment variables / key vault (prod), placeholder in committed config. Flag even in "just a sample" files — samples get copied.

### 3.6 Weak password hashing / homemade crypto — Blocker

**Detect:** `MD5`, `SHA1`, `SHA256` (etc.) applied to passwords; `new Random()` for tokens; comparing secrets with `==`.
**Why:** Fast hashes are brute-forceable offline; `Random` is predictable; `==` leaks timing.
**Fix:** `PasswordHasher<T>` (ASP.NET Identity, PBKDF2) or bcrypt/argon2; `RandomNumberGenerator` for tokens; `CryptographicOperations.FixedTimeEquals` for comparisons.

### 3.7 Sensitive data in logs — Warning

**Detect:** Log calls whose arguments include passwords, tokens, full card/ID numbers, request bodies of auth endpoints.
**Why:** Logs outlive the request, get shipped to third parties, and are rarely access-controlled like the DB is.
**Fix:** Log ids and outcomes, never credentials; redact before logging.

---

## 4. Correctness

### 4.1 Swallowed exception — Warning (Blocker when it hides data loss)

**Detect:** `catch\s*(\([^)]*\))?\s*\{\s*\}` (empty catch), or a catch that only logs and then continues as if the operation succeeded.
**Why:** The failure is converted into silent wrong behavior — the caller believes the write/side-effect happened.
**Fix:** Catch only what you can handle; otherwise let it propagate to the pipeline's exception handling. If continuing is genuinely correct, a comment must say why.

### 4.2 `throw ex;` — Suggestion

**Detect:** `throw\s+\w+;` inside a `catch (… ex)`.
**Why:** Resets the stack trace to the rethrow site; the original failure location is lost from every log.
**Fix:** bare `throw;` (or `ExceptionDispatchInfo` when rethrowing elsewhere).

### 4.3 Culture-sensitive string handling — Warning

**Detect:** `ToLower()` / `ToUpper()` used for comparison; `==` / `Contains` / `StartsWith` on strings where case-insensitivity is intended; `DateTime.Parse` / `decimal.Parse` on machine-generated strings without `CultureInfo.InvariantCulture`.
**Why:** Results change with the server's culture — the Turkish-I bug (`"ID".ToLower()` → `"ıd"`), `decimal.Parse("1.5")` → 15 on a comma-decimal culture.
**Fix:** `string.Equals(a, b, StringComparison.OrdinalIgnoreCase)`, `Contains(x, StringComparison.OrdinalIgnoreCase)`, `Parse(s, CultureInfo.InvariantCulture)`.

### 4.4 `float`/`double` for money — Blocker

**Detect:** `float` or `double` fields/properties/parameters named or used as amounts, prices, totals, rates applied to money.
**Why:** Binary floating point can't represent 0.1; sums drift by cents and reconciliation fails.
**Fix:** `decimal` end to end, including the EF column type.

### 4.5 Null-forgiveness and nullable mismatches — Warning

**Detect:** New `!` (null-forgiving operator) in the diff — `\w!\.`|`!\)`|`!;` — and `#nullable disable`; also `FirstOrDefault` / `Find` results dereferenced without a null check.
**Why:** `!` doesn't make the value non-null, it silences the one tool that was warning about the `NullReferenceException`.
**Fix:** Handle the null (guard, `?? throw`, return 404) or fix the type so it can't be null.
**Not a finding when:** the non-nullness is structurally guaranteed and the guarantee is visible nearby (e.g. checked two lines up in a way flow analysis can't see).

### 4.6 `DateTime.Now` in business logic — Suggestion (Warning if mixed with `UtcNow` on the same data)

**Detect:** `DateTime\.Now\b`.
**Why:** Server-local time changes with deployment region and DST; comparing it against stored UTC values is off by the offset twice a year.
**Fix:** `DateTime.UtcNow` / `DateTimeOffset.UtcNow`; inject `TimeProvider` (.NET 8+) where testability matters.

### 4.7 Changed behavior with unread callers — Warning

**Detect:** Not a grep — this is the step-2 caller check. A changed method's contract (nullability, units, order of results, thrown exceptions, defaults) no longer matches what a caller assumes.
**Why:** The diff compiles; the bug is at the call site nobody re-read.
**Fix:** Cite both sides: the changed line and the caller line that's now wrong.

---

## 5. Resources & lifetimes

### 5.1 Captive dependency — Blocker

**Detect:** A service registered as `AddSingleton` whose constructor takes a scoped service (`DbContext`, anything `AddScoped`). Cross-reference constructors of new/changed classes against `Program.cs` registrations.
**Why:** The singleton holds the "scoped" instance forever: one `DbContext` shared by all requests → threading errors (see 1.5) and stale tracked entities. Dev-time scope validation only catches direct constructor injection, not factories or `IServiceProvider` use.
**Fix:** Inject `IServiceScopeFactory`/`IDbContextFactory<T>` and create per-operation scopes, or make the outer service scoped.

### 5.2 `new HttpClient()` per call — Warning

**Detect:** `new HttpClient(` in a method body (not a factory/DI setup).
**Why:** Each instance owns a connection pool; per-call creation leaks sockets into `TIME_WAIT` → `SocketException` under load. A long-lived static one instead ignores DNS changes.
**Fix:** `IHttpClientFactory` (`AddHttpClient`), typed clients.

### 5.3 Undisposed `IDisposable` / `IAsyncDisposable` — Warning

**Detect:** `new` of disposable types (`FileStream`, `SqlConnection`, `MemoryStream` handed to nothing, `CancellationTokenSource`, EF context via factory) without `using` / `await using` / a clear ownership transfer.
**Why:** Handles and connections outlive the operation; connection pools drain; linked `CancellationTokenSource` chains leak timers.
**Fix:** `using var` / `await using var`; when ownership transfers (returned to caller, passed to a response), say so and don't report.

### 5.4 Static mutable state — Warning

**Detect:** `static` fields that are not `readonly` + immutable, especially collections (`static List<`, `static Dictionary<` without `Concurrent`/`Frozen`/`Immutable`).
**Why:** Shared across all requests with no synchronization — corruption under concurrency, and state bleeding between tenants/tests.
**Fix:** Instance state with an appropriate DI lifetime, `ConcurrentDictionary`, or `FrozenDictionary` for build-once lookup data.

---

## 6. API contract (ASP.NET Core)

### 6.1 EF entities on the wire — Warning

**Detect:** Endpoint/controller return types (or `Results.Ok(x)` arguments) that are `DbSet` entity types.
**Why:** Serializes lazy navigation graphs (cycles → 500s), leaks columns you'll add later (password hashes, soft-delete flags), and welds the DB schema to the public contract.
**Fix:** Response DTOs via `Select` projection.

### 6.2 Wrong or unstated status codes — Suggestion (Warning for lying codes)

**Detect:** `return Ok()` on create (should be 201 + location), missing not-found path (`FirstOrDefaultAsync` result returned directly — null becomes 204 or a serialized `null`), catch blocks returning 200 with an error payload.
**Why:** Clients branch on status codes; a 200-with-error breaks every generic client and retry policy.
**Fix:** `TypedResults.Created/NotFound/ValidationProblem`; RFC 9457 `ProblemDetails` for errors. (The `api-design` skill in this repo covers the full contract if the user wants a deeper API review.)

### 6.3 Missing input validation — Warning

**Detect:** Request DTOs whose fields are used (persisted, queried, used in calculations) with no validation attributes, FluentValidation validator, or manual checks — especially lengths on strings that hit indexed columns, ranges on quantities/amounts, and pagination parameters (an unbounded `pageSize` is a self-inflicted DoS).
**Why:** Garbage reaches the domain and the DB; unbounded pagination is a self-DoS.
**Fix:** Validate at the edge; clamp pagination (`pageSize = Math.Clamp(pageSize, 1, 100)`).

### 6.4 Middleware order — Blocker when auth is affected

**Detect:** In `Program.cs` diffs: `UseAuthorization()` before `UseAuthentication()`; `UseCors` after endpoints; exception-handling middleware registered after the things it should cover.
**Why:** Order is execution order. Authorization before authentication evaluates policies against an anonymous user.
**Fix:** Routing → CORS → Authentication → Authorization → endpoints.

---

## 7. Performance

Only flag performance findings on paths with evidence of heat: request handling, loops over unbounded data, or code the diff itself says is hot. Micro-optimizations elsewhere are noise — skip them.

### 7.1 Sync I/O on the request path — Warning

**Detect:** `File.ReadAllText`, `stream.Read(`, `.CopyTo(` (non-async) inside endpoints/handlers.
**Why:** Blocks a thread-pool thread per request — same starvation math as 1.2. Kestrel rejects sync body reads by default (`AllowSynchronousIO`).
**Fix:** The `Async` counterparts with the request's `CancellationToken`.

### 7.2 Per-call `JsonSerializerOptions` / `Regex` — Warning

**Detect:** `new JsonSerializerOptions` or `new Regex(` inside a method that runs per request/per item.
**Why:** `JsonSerializerOptions` caches type metadata — rebuilding it per call redoes reflection every time. Same for `Regex` compilation.
**Fix:** `static readonly` instance, or `[GeneratedRegex]` (.NET 7+).

### 7.3 Allocation patterns in hot loops — Suggestion

**Detect:** String concatenation with `+=` in a loop; LINQ chains re-enumerated (`IEnumerable` consumed twice — also a *correctness* bug if the source is a live query); `Count() > 0` where `Any()` reads better and stops early.
**Fix:** `StringBuilder`; materialize once with `ToList()` when enumerating twice; `Any()`.

---

## 8. Tests

### 8.1 Behavior changed, no test touched — Warning

**Detect:** The diff changes logic in a project that has a test project, and no test file appears in the diff.
**Why:** Either the behavior isn't covered (the change is unverified) or a test now lies about what the code does.
**Fix:** Name the specific changed behavior that deserves a test — not a generic "add tests".

### 8.2 Assertions that can't fail — Warning

**Detect:** In changed tests: `Assert.NotNull` on a value the compiler already knows is non-null, asserting on the mock's own setup return value, `try/catch` around the assertion, no assertion at all (test only checks "doesn't throw").
**Why:** A green test that can't go red is worse than no test — it certifies nothing while looking like coverage.
**Fix:** Assert on observable behavior of the system under test: returned values, persisted state, calls to boundaries.

---

## Reporting discipline

- One finding per root cause: if a missing DTO causes over-posting *and* entity-on-the-wire, that's one card (the higher severity) citing both symptoms.
- When two categories detect the same lines, keep the more specific one.
- Quote minimally: the offending line ± the 2–4 lines needed to see the problem, never whole methods.
- If a pattern matched but a counter-signal cleared it, and the user would plausibly ask about it, one line in chat ("checked X, it's covered by the fallback auth policy") — not a card in the report.
