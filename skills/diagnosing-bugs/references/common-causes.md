# Common Causes by Symptom (.NET)

A catalog for Phase 3: find the section matching your symptom fingerprint and use its entries as hypothesis candidates. Each entry gives the cause, a **falsifiable prediction** you can adapt, and where useful a grep pattern to locate suspects. These are ranked roughly by how often they turn out to be the answer in .NET codebases — but your minimized repro's load-bearing elements outrank base rates: if removing the culture setting turned the loop green, culture entries jump to the top regardless of position here.

Grep patterns are ripgrep-compatible regex: `rg -n "<pattern>" --type cs`.

## Contents

- [A. Hangs and deadlocks](#a-hangs-and-deadlocks)
- [B. Intermittent / flaky failures](#b-intermittent--flaky-failures)
- [C. Works locally, fails in CI or production](#c-works-locally-fails-in-ci-or-production)
- [D. Wrong or stale data](#d-wrong-or-stale-data)
- [E. Exceptions decoded](#e-exceptions-decoded)
- [F. Slow / performance regressions](#f-slow--performance-regressions)

---

## A. Hangs and deadlocks

### A1. Sync-over-async blocking
- **Cause**: `.Result` / `.Wait()` / `GetAwaiter().GetResult()` on the request path. Under load, blocked thread-pool threads leave no thread for the continuations they're waiting on.
- **Fingerprint**: fine with one request, hangs under load; `ThreadPool Queue Length` climbs in `dotnet-counters`.
- **Grep**: `\.Result\b|\.Wait\(\)|GetAwaiter\(\)\.GetResult\(\)`
- **Prediction**: making that call `await`ed (or temporarily `ThreadPool.SetMinThreads(200, 200)`) removes or shifts the hang threshold.

### A2. Lock held across a slow or awaited operation
- **Cause**: `lock` won't compile around `await`, so people switch to `SemaphoreSlim` — and then miss a release on an exception path, or hold it during slow I/O.
- **Grep**: `SemaphoreSlim` — check every `WaitAsync` has its `Release` in a `finally`.
- **Prediction**: `dotnet-stack report` during the hang shows threads queued in `SemaphoreSlim.WaitAsync`; the holder's stack shows what it's stuck on.

### A3. HttpClient call with no timeout or cancellation
- **Cause**: default `HttpClient.Timeout` is 100s, and handlers/retry layers can extend it; a dead upstream turns into a "hang".
- **Prediction**: the hang always lasts a suspiciously round duration (100s, or retries × timeout); pointing the client at a stub (feedback-loops #7) makes it green.

### A4. Missing `ConfigureAwait`/context only in legacy hosts
- **Cause**: classic sync-context deadlock needs a UI thread or legacy ASP.NET — ASP.NET Core has no sync context. Rank this **low** unless the code is WPF/WinForms/MAUI or a library consumed by one.
- **Prediction**: same call from a console harness (no sync context) completes; from the UI thread it deadlocks.

## B. Intermittent / flaky failures

### B1. Shared mutable state across tests or requests
- **Cause**: `static` fields, singletons holding per-request data, or a test fixture mutated by one test and read by another.
- **Fingerprint**: test passes alone, fails in the suite (or vice versa); failure correlates with execution order.
- **Grep**: `static (?!readonly)` in product code; in tests, fields mutated in `[Fact]`s of a shared class fixture.
- **Prediction**: disabling xunit parallelization (`[assembly: CollectionBehavior(DisableTestParallelization = true)]`) or running the test alone changes the failure rate.

### B2. Check-then-act race
- **Cause**: `if (!dict.ContainsKey(k)) dict.Add(k, v)`, lazy init without a lock, "SELECT then INSERT" without a constraint.
- **Prediction**: a tagged `Thread.Sleep(10)` between the check and the act makes it fail ~always; `Parallel.For` around the operation (feedback-loops #6) reproduces on demand.

### B3. Time-boundary dependence
- **Cause**: `DateTime.Now` crossing midnight/DST/month-end between two reads; comparing local to UTC.
- **Grep**: `DateTime\.(Now|Today)\b` — each hit is a candidate; mixing with `UtcNow` in the same flow is a stronger one.
- **Prediction**: with `FakeTimeProvider` pinned just before the boundary and advanced across it, the loop goes red deterministically.

### B4. Fire-and-forget / `async void` losing exceptions
- **Cause**: an unawaited task or `async void` method throws; the work silently didn't happen, and the failure surfaces later as missing data — or crashes the process at an unrelated moment.
- **Grep**: `async void` (only legitimate on event handlers); `\b_\s*=\s*\w+Async\(|Task\.Run\([^)]*\);` unawaited.
- **Prediction**: the first-chance exception hook (instrumentation reference) shows an exception at the suspect time that never appears in logs.

### B5. Port, file, or resource collision between parallel runs
- **Cause**: hardcoded port, shared temp filename, same database rows touched by parallel tests.
- **Prediction**: failure only occurs when two runs overlap; per-run isolation (port 0, `Directory.CreateTempSubdirectory()`, unique keys) makes 100 runs green.

## C. Works locally, fails in CI or production

### C1. Culture-sensitive parsing/formatting
- **Cause**: `DateTime.Parse`, `decimal.Parse`, `double.ToString` without `CultureInfo` — dev machine is (say) en-US, server is de-DE or invariant: `"1.5"` parses as 15, dates flip day/month.
- **Grep**: `\.(Parse|TryParse|ToString)\(` without a `CultureInfo` argument nearby, on numeric/date types.
- **Prediction**: `CultureInfo.DefaultThreadCurrentCulture = CultureInfo.GetCultureInfo("<server culture>")` at the top of the repro turns it red locally.

### C2. Case-sensitive filesystem / path separators
- **Cause**: Windows dev, Linux CI/prod: `Assets/logo.PNG` vs `assets/logo.png`, or hand-built `"dir\\file"` paths.
- **Grep**: `"[^"]*\\\\[^"]*"` (backslash paths); compare failing filename casing against the repo's.
- **Prediction**: the exact file that "exists locally" is absent on Linux with that casing; `Path.Combine` + exact-case fixes it.

### C3. Configuration/environment divergence
- **Cause**: value comes from `appsettings.Development.json`, user-secrets, or a local env var that CI/prod doesn't have; or `ASPNETCORE_ENVIRONMENT` differs so a whole branch of `Program.cs` doesn't run.
- **Prediction**: logging the resolved value (`builder.Configuration["Payments:ApiUrl"]`, tagged) in both environments shows different values. This is one of the highest base-rate causes for this symptom class — check it first.

### C4. Database drift / missing migration
- **Cause**: local db got a migration (or manual tweak) the target never received.
- **Prediction**: `dotnet ef migrations list` on the target's connection shows pending migrations; the failing SQL names a column that isn't in the target schema.

### C5. Timezone of the server
- **Cause**: `DateTime.Now`/`DateTime.Today` on a UTC server vs. local dev machine — "today's" records shift by your UTC offset.
- **Grep**: `DateTime\.(Now|Today)\b`
- **Prediction**: `TZ=UTC dotnet test ...` (Linux) or `FakeTimeProvider` at a UTC time near your local midnight reproduces locally.

### C6. Release-build or trimming behavior
- **Cause**: `#if DEBUG` branches, `Debug.Assert` side effects, or (for published trimmed/AOT apps) reflection-based serialization losing members.
- **Prediction**: `dotnet test -c Release` (or running the published output) reproduces locally; for trimming, the missing member reappears with trimming disabled.

## D. Wrong or stale data

### D1. DbContext identity map returns the already-tracked instance
- **Cause**: two queries in one context for the same key return the **same instance** — mutations from the first survive into the "fresh" second read; or a no-tracking query is expected to see uncommitted local changes and doesn't.
- **Prediction**: logging `RuntimeHelpers.GetHashCode(entity)` at both sites shows the same hash; using a fresh context (or `AsNoTracking` on the first query) changes the result.

### D2. DbContext lifetime wrong (captive or shared)
- **Cause**: `DbContext` resolved into a singleton (captive — lives forever, cache grows stale, never sees others' writes) or shared across parallel tasks.
- **Grep**: check `Program.cs` registrations — any singleton whose constructor takes `DbContext` or a scoped service.
- **Prediction**: for staleness — a second process's write is invisible until restart; making the consumer scoped fixes it. For corruption — see E2 below.

### D3. Cache without invalidation or with a colliding key
- **Cause**: `IMemoryCache`/`ConcurrentDictionary` cache written once, never evicted on update; or key built without a distinguishing part (`$"user"` instead of `$"user:{id}"`).
- **Grep**: `IMemoryCache|GetOrCreate|ConcurrentDictionary`
- **Prediction**: the stale value is exactly the *first* value ever computed; bypassing the cache (tagged) makes the loop green.

### D4. JSON serialization mismatch
- **Cause**: property arrives as default/null because of casing (`System.Text.Json` deserialization is case-sensitive by default outside ASP.NET Core's web defaults), a missing setter/`init` mismatch, enum sent as string but bound as int, or `[JsonPropertyName]` divergence between client and server contracts.
- **Prediction**: logging the raw JSON string right before deserialization shows the field present — so the loss is in binding, and deserializing that exact string in a unit test with the app's `JsonSerializerOptions` reproduces it.

### D5. Money in `double` / float comparison
- **Cause**: binary floating point: `0.1 + 0.2 != 0.3`; totals off by a cent after many operations.
- **Grep**: `double|float` on price/amount/quantity fields.
- **Prediction**: the same arithmetic in `decimal` gives the expected value.

### D6. Culture-sensitive string comparison/sorting
- **Cause**: `ToUpper()`/`ToLower()` comparisons, `string.Compare` without `StringComparison` — the Turkish-I problem, ordinal-vs-culture sort differences between machines.
- **Grep**: `ToUpper\(\)|ToLower\(\)` used for comparison; `Compare(To)?\(` and `Equals\(` without a `StringComparison` argument.
- **Prediction**: switching the comparison to `StringComparison.OrdinalIgnoreCase` changes the result; or pinning culture to `tr-TR` makes the loop red locally.

## E. Exceptions decoded

The exception message often names the cause precisely — match it here before hypothesizing more broadly.

### E1. `ObjectDisposedException: Cannot access a disposed context/object`
- **Cause**: work outlived the request scope: fire-and-forget task or `async void` captured a scoped `DbContext`/service; or a missing `await` let the handler return while work continued.
- **Grep**: `async void|Task\.Run` near the throw site's call chain.
- **Prediction**: awaiting the work (or creating an `IServiceScopeFactory` scope inside the background work) removes it; the stack's bottom frames show the background origin.

### E2. `InvalidOperationException: A second operation was started on this context instance`
- **Cause**: one `DbContext` used concurrently — parallel `Task.WhenAll` over queries on the same context, a context shared by singleton, or queries kicked off without `await` in sequence.
- **Prediction**: serializing the calls (or one context per task via `IDbContextFactory`) removes it — this exception is near-proof by itself.

### E3. `InvalidOperationException: Cannot consume scoped service from singleton`
- **Cause**: captive dependency caught by the container's scope validation — a singleton constructor asks for a scoped service. Note validation runs only in Development by default, so prod may instead show D2 symptoms.
- **Prediction**: `Program.cs` registration shows the lifetimes; injecting `IServiceScopeFactory` and creating scopes per operation removes it.

### E4. `InvalidOperationException: Collection was modified; enumeration operation may not execute`
- **Cause**: mutating a collection while `foreach`-ing it — directly, via a called method, or from another thread (in which case it's B1/B2 wearing this exception).
- **Prediction**: single-threaded repro → the mutation is in the loop body's call chain; only-under-parallelism repro → it's a race, go to section B.

### E5. `NullReferenceException` deep in framework or LINQ frames
- **Cause**: usually your lambda returned null into something that dereferences it (`Select(x => x.Child.Name)` with a null `Child`), or an uninitialized navigation property before the related entity was `Include`d.
- **Prediction**: logging the first element whose suspect member is null identifies the row; adding `.Include()` (EF) or a null guard at the *source* of the null (not the crash site) makes it green.

### E6. `TaskCanceledException` from `HttpClient` with no one cancelling
- **Cause**: it's a **timeout** in disguise — `HttpClient` throws `TaskCanceledException` on timeout (on .NET 5+ the inner exception is `TimeoutException`).
- **Prediction**: the call always dies at exactly `Timeout` (default 100s, or your configured value); raising it or stubbing the upstream changes the behavior.

### E7. `InvalidOperationException: Headers are read-only, response has already started`
- **Cause**: middleware/exception handler tries to set status/headers after the body began streaming — often an exception thrown mid-response.
- **Prediction**: the log shows a first exception *before* this one; handling that first exception (or buffering) removes this secondary failure. Debug the first exception, not this one.

## F. Slow / performance regressions

Reminder from the instrumentation reference: **measure before hypothesizing** — get a baseline number and corner the slow stage by bisection first. These entries explain what you'll find when you get there.

### F1. N+1 queries
- **Cause**: lazy loading (or a query inside a `foreach`) issues one query per row.
- **Fingerprint**: EF `LogTo` output shows the same `SELECT` shape repeated N times with different parameters.
- **Prediction**: `.Include()` / projection to a DTO collapses N+1 queries into 1 and the median drops proportionally.

### F2. Missing `AsNoTracking` on large read paths
- **Cause**: change-tracker overhead on thousands of read-only entities.
- **Prediction**: adding `.AsNoTracking()` to the one query measurably drops the median; if it doesn't, revert — it wasn't this.

### F3. Multiple enumeration / `Count()` on an `IEnumerable`
- **Cause**: an `IEnumerable<T>` backed by a query or generator enumerated twice (`if (items.Any())` then `foreach`), doubling the work — or worse re-executing the database query.
- **Grep**: methods returning `IEnumerable<T>` whose callers both test and iterate it.
- **Prediction**: materializing once with `.ToList()` at the boundary halves the measured stage.

### F4. Sync I/O on the request path
- **Cause**: `File.ReadAllText`, `stream.Read`, `.Result` on I/O — each blocks a thread-pool thread; throughput collapses under concurrency long before single-request latency looks bad.
- **Fingerprint**: latency fine at 1 user, terrible at 50; thread count grows in `dotnet-counters`.
- **Prediction**: load loop (feedback-loops #6) shows throughput knee; async versions move it.

### F5. `new HttpClient()` per call
- **Cause**: socket exhaustion — each instance owns a connection pool; under load, ports run out (`SocketException: Address already in use`) and latency spikes as connections can't be reused.
- **Grep**: `new HttpClient\(`
- **Prediction**: `netstat` during the loop shows thousands of `TIME_WAIT` sockets to the upstream; switching to `IHttpClientFactory` or a static client removes them.

### F6. Catastrophic regex backtracking
- **Cause**: nested quantifiers (`(a+)+`, `(\w+\s?)*`) on non-matching input — CPU pegs on one input string, fine on others.
- **Fingerprint**: slowness depends dramatically on *which* input; profile shows all time in `System.Text.RegularExpressions`.
- **Prediction**: `new Regex(pattern, RegexOptions.None, TimeSpan.FromMilliseconds(100))` makes the bad input throw `RegexMatchTimeoutException`, confirming the pattern; rewriting the pattern (or `RegexOptions.NonBacktracking`) fixes it.

### F7. Allocation pressure / LOH churn
- **Cause**: large arrays/strings (≥85KB) allocated per request land on the Large Object Heap; gen-2 collections dominate.
- **Fingerprint**: `dotnet-counters` shows high `% Time in GC` and frequent gen-2; `dotnet-trace` top frames are GC.
- **Prediction**: pooling (`ArrayPool<byte>.Shared`) or streaming instead of buffering drops `% Time in GC` and the median together.

---

If nothing here matches, generate hypotheses from the minimized repro directly: each load-bearing element (the thing that, removed, turns the loop green) implicates the code that consumes it. Read that consuming code — *now* you have earned the right to read code with a theory in mind.
