# Instrumentation (.NET)

How to gather evidence for a specific hypothesis. Read this before adding any instrumentation. Two rules govern everything here:

1. **Every probe maps to one prediction.** Before adding a log line or attaching a tool, say which Phase 3 hypothesis it will confirm or falsify. "Log everything and grep" is not a probe — it produces noise that feels like progress.
2. **Everything temporary is tagged.** Pick one random 4-hex tag per debugging session (e.g. `a4f2`). Every debug log line starts with `[DEBUG-a4f2]`, every temporary code change carries `// DEBUG-a4f2`. Cleanup is then one command: `grep -rn "DEBUG-a4f2" .` — and it must return zero hits before you report. Untagged debug logs are the ones that ship.

## Contents

- [Tagged log probes](#tagged-log-probes)
- [Turning up framework logging](#turning-up-framework-logging)
- [Seeing EF Core's actual SQL](#seeing-ef-cores-actual-sql)
- [Finding swallowed exceptions](#finding-swallowed-exceptions)
- [Diagnosing hangs and deadlocks](#diagnosing-hangs-and-deadlocks)
- [Performance regression workflow](#performance-regression-workflow)
- [Memory leaks](#memory-leaks)

## Tagged log probes

Place probes at the boundaries that **distinguish hypotheses** — the value going into the suspect call and the value coming out. Two well-placed lines beat twenty scattered ones.

In product code (temporary):

```csharp
Console.Error.WriteLine($"[DEBUG-a4f2] before Save: entity.Id={entity.Id} state={ctx.Entry(entity).State}"); // DEBUG-a4f2
```

`Console.Error` is deliberate: it bypasses `ILogger` configuration, so it appears no matter what log levels say, and it can't be mistaken for a permanent log. Include *identity* where object aliasing is suspected: `RuntimeHelpers.GetHashCode(entity)` prints a reference hash — two log lines with the same hash mean the same instance.

Inside an xUnit test, `Console.WriteLine` may be swallowed; use the output helper:

```csharp
public class ReproTests(ITestOutputHelper output)
{
    [Fact]
    public void Repro_x()
    {
        output.WriteLine($"[DEBUG-a4f2] got: {value}");
        ...
    }
}
```

and run with `dotnet test --logger "console;verbosity=detailed"` to see it.

For probes inside code you cannot edit (a NuGet package), log around the call site instead — arguments in, result out, exception if thrown.

## Turning up framework logging

When the hypothesis involves the framework itself (model binding rejecting a field, auth failing before your code runs, middleware short-circuiting), raise the log level **without editing appsettings.json** — environment variables override it and can't be accidentally committed:

```powershell
$env:Logging__LogLevel__Default = "Debug"
$env:Logging__LogLevel__Microsoft_AspNetCore = "Debug"
dotnet run --project src/MyApp.Api
```

(bash: `Logging__LogLevel__Default=Debug dotnet run ...`.)

Useful specific categories: `Microsoft.AspNetCore.Routing` (why a request matched/missed an endpoint), `Microsoft.AspNetCore.Authorization` (which policy failed), `Microsoft.AspNetCore.Mvc.ModelBinding` (why a property arrived null). Debug-level ASP.NET Core logging is voluminous — pipe to a file and search for the request path.

To see full requests/responses, add HTTP logging temporarily (tag both lines):

```csharp
builder.Services.AddHttpLogging(o => o.LoggingFields = HttpLoggingFields.All); // DEBUG-a4f2
app.UseHttpLogging(); // DEBUG-a4f2 — must come before the middleware you're inspecting
```

## Seeing EF Core's actual SQL

For wrong-data and performance hypotheses, read the SQL EF actually generates — never reason from the LINQ. Temporary, on the context options:

```csharp
optionsBuilder
    .LogTo(s => Console.Error.WriteLine($"[DEBUG-a4f2] {s}"), LogLevel.Information) // DEBUG-a4f2
    .EnableSensitiveDataLogging(); // DEBUG-a4f2 — shows parameter values; NEVER ships
```

What to look for in the output:

- **The same `SELECT` repeated N times with different ids** → N+1 (lazy loading or a query inside a loop).
- **A `SELECT` without the expected `WHERE`** → the filter ran client-side; look for the `CoreEventId.RowLimitingOperationWithoutOrderByWarning` / client-evaluation warnings in the same output.
- **No `UPDATE` at `SaveChanges`** → the entity isn't tracked (wrong context instance, or `AsNoTracking` upstream).
- **A query you didn't expect at all** → an accessed lazy navigation property.

One-off queries against the dev database to verify data state: prefer reading via a quick harness (recipe #4) using the same `DbContext`, so you see what EF sees (including query filters).

## Finding swallowed exceptions

When behavior silently goes wrong and the hypothesis is "something throws and gets eaten" (empty `catch`, `async void`, fire-and-forget task):

```csharp
AppDomain.CurrentDomain.FirstChanceException += (_, e) =>
    Console.Error.WriteLine($"[DEBUG-a4f2] first-chance: {e.Exception.GetType().Name}: {e.Exception.Message}"); // DEBUG-a4f2
```

This fires for **every** exception at throw time, before any catch — including ones later handled legitimately, so expect noise; filter by exception type or namespace if needed. Place it at the top of `Program.cs` or the test. For unobserved task exceptions specifically, also hook `TaskScheduler.UnobservedTaskException` (note: it fires at GC time, so force `GC.Collect(); GC.WaitForPendingFinalizers();` at the end of the repro to flush it).

## Diagnosing hangs and deadlocks

A hang cannot be logged into visibility — you need the stacks of every thread at the moment of the hang. Install the tools once:

```bash
dotnet tool install -g dotnet-counters dotnet-dump dotnet-stack dotnet-trace dotnet-gcdump
```

While the process is hung (find the PID with `dotnet-counters ps`):

```bash
dotnet-stack report -p <pid>          # quick: all managed stacks to stdout
dotnet-dump collect -p <pid>          # thorough: full dump for offline analysis
dotnet-dump analyze <dumpfile>        # then inside: clrstacks, clrthreads, syncblk
```

How to read what you get:

- **Sync-over-async deadlock / starvation**: many thread-pool threads blocked in frames like `Monitor.Wait` under `Task.InternalWait` / `GetResultCore` — someone called `.Result`/`.Wait()` and the continuation has no thread to run on. Confirm with `dotnet-counters monitor --counters System.Runtime -p <pid>`: `ThreadPool Queue Length` climbing while `ThreadPool Thread Count` creeps up one per second is the starvation signature.
- **Classic lock deadlock**: in `dotnet-dump analyze`, `syncblk` lists monitors and owning threads; two threads each owning a lock the other waits on is your answer — the stacks name the exact code.
- **Not actually hung, just slow**: stacks show normal work frames that differ between samples taken 10s apart. That's a performance problem — switch to the perf workflow below.

## Performance regression workflow

Never diagnose performance by reading code — plausible-looking culprits are wrong often enough that unmeasured "optimizations" regularly make things slower. The workflow is: **baseline → corner it by bisection → fix → re-measure**.

**1. Baseline.** A timing harness around the slow operation (median, not first run — first run pays JIT):

```csharp
// warmup
for (var i = 0; i < 3; i++) await sut.RunAsync(input);

var samples = new List<long>();
for (var i = 0; i < 10; i++)
{
    var sw = Stopwatch.StartNew();
    await sut.RunAsync(input);
    samples.Add(sw.ElapsedMilliseconds);
}
samples.Sort();
Console.Error.WriteLine($"[DEBUG-a4f2] median={samples[5]}ms all=[{string.Join(",", samples)}]");
```

For a whole-process view while the loop runs: `dotnet-counters monitor -p <pid> --counters System.Runtime,Microsoft.AspNetCore.Hosting` — watch CPU, GC heap size, gen collections, thread-pool queue.

**2. Corner it.** Two bisection axes, pick per the symptom:

- **Time axis** — "it got slow at some point": `git bisect run` (feedback-loops recipe #5) with the timing harness asserting `median < threshold`.
- **Pipeline axis** — "this operation is slow now": wrap each stage of the operation in the tagged stopwatch until one stage owns the time; recurse into that stage. Where stages are opaque, capture a CPU profile instead: `dotnet-trace collect -p <pid> --format speedscope` while the loop runs, open the `.speedscope.json` at https://speedscope.app (or read the top frames with any text tooling) — the widest frames are the answer.

**3. Verify the fix numerically.** Re-run the same harness; report before/after medians. If the numbers don't move, the fix was wrong regardless of how right it looked — revert it.

`BenchmarkDotNet` is for the endgame only — micro-optimizing a specific method you've already convicted — never for finding the problem.

## Memory leaks

Symptom: heap grows without bound, or `OutOfMemoryException` after hours. Loop = an action you can repeat that should be memory-neutral.

```bash
dotnet-counters monitor -p <pid> --counters System.Runtime
# watch "GC Heap Size" across 100 repetitions of the action — steady growth = leak

dotnet-gcdump collect -p <pid>    # snapshot 1
# ... repeat the action 100x ...
dotnet-gcdump collect -p <pid>    # snapshot 2
```

Compare the two snapshots (`dotnet-gcdump report <file>` prints object counts by type): the type whose count grew by ~100 is the leaked object. The usual .NET suspects for *why* it's still rooted: an event handler subscribed but never unsubscribed, a static collection used as a cache with no eviction, `IMemoryCache` entries with no size/expiry, timers not disposed, or a captive dependency holding a scoped object in a singleton.
