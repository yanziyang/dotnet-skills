# Feedback Loop Recipes (.NET)

Eight ways to build a red/green command for a .NET bug, in the order you should prefer them. Each recipe is complete — copy it and adapt names. Whatever you build, run it immediately and paste the red output before moving on; a loop you haven't seen red is a hope, not a loop.

Naming convention used throughout: temporary repro tests are named `Repro_<short-bug-slug>` so they are easy to filter and easy to find later. If the repro test becomes the permanent regression test in Phase 5, rename it to describe the behavior (e.g. `Total_excludes_archived_orders`).

## Contents

1. [Failing xUnit test](#1-failing-xunit-test) — pure logic bugs
2. [WebApplicationFactory integration test](#2-webapplicationfactory-integration-test) — endpoint/DI/serialization bugs
3. [HTTP script against a running server](#3-http-script-against-a-running-server) — needs the real host/config
4. [Throwaway console harness](#4-throwaway-console-harness) — no test project available
5. [git bisect run](#5-git-bisect-run) — regressions ("used to work")
6. [Amplification loop for flaky bugs](#6-amplification-loop-for-flaky-bugs)
7. [Determinism toolkit](#7-determinism-toolkit) — pinning time, random, culture, network, ports
8. [Human-in-the-loop last resort](#8-human-in-the-loop-last-resort)

---

## 1. Failing xUnit test

For bugs in a method or class you can construct and call directly. Put it in the **existing** test project (new test projects cost minutes; a new test file costs seconds).

```csharp
public class ReproTests
{
    [Fact]
    public void Repro_total_includes_archived_orders()
    {
        var orders = new[]
        {
            new Order { Amount = 100m, IsArchived = false },
            new Order { Amount = 50m,  IsArchived = true  },
        };

        var total = new OrderCalculator().Total(orders);

        Assert.Equal(100m, total); // currently returns 150m — archived is not excluded
    }
}
```

Run only this test — that's what makes the loop fast:

```bash
dotnet test tests/MyApp.Tests --filter "FullyQualifiedName~Repro_total_includes_archived"
```

Tighten it further with `--no-restore`, and if you're iterating on the product code (not the test), `dotnet watch test --project tests/MyApp.Tests --filter ...` re-runs on save.

Sharpen the assertion to the **specific symptom**: assert the wrong value (`150m` appearing) is gone, not merely "doesn't throw". A loose assertion goes green for the wrong reasons.

## 2. WebApplicationFactory integration test

For bugs that live in the ASP.NET Core pipeline: routing, model binding, filters, middleware order, DI lifetimes, JSON serialization, auth. This boots the real `Program` in-memory — no port, no process management, seconds per run.

Requirements: package `Microsoft.AspNetCore.Mvc.Testing` in the test project, and for top-level-statement apps, `Program` must be visible — add this once at the bottom of `Program.cs` if it isn't already there:

```csharp
public partial class Program { }
```

The test, with a service override so the loop doesn't need a real database:

```csharp
public class ReproApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;

    public ReproApiTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                // Swap the real DbContext for SQLite in-memory
                services.RemoveAll<DbContextOptions<AppDbContext>>();
                var conn = new SqliteConnection("DataSource=:memory:");
                conn.Open(); // keep open — closing drops the in-memory db
                services.AddDbContext<AppDbContext>(o => o.UseSqlite(conn));
            });
        });
    }

    [Fact]
    public async Task Repro_put_returns_500_when_name_is_null()
    {
        using var client = _factory.CreateClient();

        var response = await client.PutAsJsonAsync("/api/products/1",
            new { name = (string?)null, price = 10 });

        // Symptom: 500 InvalidOperationException; expected: 400 validation problem
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }
}
```

Seed data inside the test via a scope: `using var scope = _factory.Services.CreateScope();` then resolve `AppDbContext`, add rows, `SaveChanges`, and `EnsureCreated()` first.

Caveat: SQLite doesn't reproduce provider-specific behavior (SQL Server collations, sequences, `datetimeoffset` precision, deadlocks). If the hypothesis space includes the database engine itself, use the real provider — Testcontainers (`Testcontainers.MsSql` / `Testcontainers.PostgreSql`) if Docker is available; otherwise a script against a dev database (recipe #3).

## 3. HTTP script against a running server

When the bug needs the real host — real config, real database, HTTPS, a specific environment. Start the server once in the background, then loop the script.

Start (leave running):

```bash
dotnet run --project src/MyApp.Api --launch-profile https &
```

PowerShell loop with a hard assertion and exit code:

```powershell
$r = Invoke-RestMethod -Uri "https://localhost:7042/api/orders/9" -SkipCertificateCheck
if ($r.total -eq 150) { Write-Host "RED: total=150 (includes archived)"; exit 1 }
else { Write-Host "GREEN: total=$($r.total)"; exit 0 }
```

bash/curl equivalent:

```bash
total=$(curl -sk https://localhost:7042/api/orders/9 | jq .total)
if [ "$total" = "150" ]; then echo "RED: total=$total"; exit 1; fi
echo "GREEN: total=$total"; exit 0
```

Save it as a script in the scratchpad/temp directory (never in the repo), so the loop is one command. Remember the server must be **restarted after each product-code change** — that makes this loop slower than #1/#2; use it only when the in-memory factory genuinely can't host the bug.

## 4. Throwaway console harness

For library/worker code with no test project, or when you need a tight call-the-method-in-a-loop rig. Create it **outside the solution** (don't `dotnet sln add` it — it must never ship):

```bash
dotnet new console -o /tmp/debug-harness
dotnet add /tmp/debug-harness reference src/MyApp.Core/MyApp.Core.csproj
```

`Program.cs` — exercise the bug path, exit nonzero on the symptom:

```csharp
using MyApp.Core;

var result = new PriceFormatter().Format(1234.5m, "de-DE");
Console.WriteLine($"got: {result}");
if (result != "1.234,50 €") { Console.WriteLine("RED"); return 1; }
Console.WriteLine("GREEN");
return 0;
```

Loop: `dotnet run --project /tmp/debug-harness`. Delete the folder in Phase 6.

## 5. git bisect run

For regressions. First build a red/green command with recipe #1–#4, then let git binary-search the history. The catch: the repro test file usually doesn't exist in old commits, and checked-out commits would overwrite it. Solution — keep the repro **outside the repo** and copy it in per step via a bisect script:

`/tmp/bisect-step.sh`:

```bash
#!/bin/sh
cp /tmp/Repro_total.cs tests/MyApp.Tests/Repro_total.cs
dotnet test tests/MyApp.Tests --filter "FullyQualifiedName~Repro_total" --no-restore
status=$?
rm -f tests/MyApp.Tests/Repro_total.cs   # leave the tree clean for the next checkout
exit $status
```

Then:

```bash
git bisect start
git bisect bad HEAD
git bisect good v2.3.0        # last version known to work
git bisect run sh /tmp/bisect-step.sh
git bisect reset
```

`git bisect run` treats exit 0 as good, 1–124 as bad. If some historical commits don't build for unrelated reasons, exit `125` from the script to skip them (`dotnet build || exit 125` before the test). The answer — the first bad commit — is itself strong evidence for Phase 3: read that commit's diff and derive hypotheses from it.

## 6. Amplification loop for flaky bugs

An intermittent bug must be made frequent before it can be diagnosed — aim for a reproduction rate of ~50%+ so a probe result means something. Techniques, in order:

**Measure the current rate** (also your loop — the count is the signal):

```powershell
$fail = 0
1..100 | ForEach-Object {
    dotnet test tests/MyApp.Tests --filter "FullyQualifiedName~Repro_race" --no-restore *> $null
    if ($LASTEXITCODE -ne 0) { $fail++ }
}
Write-Host "failed $fail/100"
```

```bash
fail=0
for i in $(seq 1 100); do
  dotnet test tests/MyApp.Tests --filter "FullyQualifiedName~Repro_race" --no-restore >/dev/null 2>&1 || fail=$((fail+1))
done
echo "failed $fail/100"
```

**Raise the rate**:

- **Loop inside the test** — 1000 iterations of the suspect operation inside one `[Fact]` is far cheaper than 1000 process starts.
- **Force real concurrency** at the suspect call site:

  ```csharp
  [Fact]
  public async Task Repro_counter_loses_increments_under_parallelism()
  {
      var sut = new HitCounter();
      await Task.WhenAll(Enumerable.Range(0, 8)
          .Select(_ => Task.Run(() => { for (var i = 0; i < 10_000; i++) sut.Increment(); })));
      Assert.Equal(80_000, sut.Count); // red when increments race
  }
  ```

- **Starve the thread pool** to widen async timing windows: `ThreadPool.SetMinThreads(1, 1);` at test start (tag it `// DEBUG-<tag>` — it must not survive cleanup).
- **Widen the race window**: a temporary `Thread.Sleep(10)` or `await Task.Yield()` inserted between the check and the act of a suspected check-then-act race turns a 1% repro into ~100%. Tag it; it is instrumentation, not a fix.
- **Kill test-order effects**: run the suspect test alone, then with the suite. If it only fails with the suite, the hypothesis is shared state — bisect *which other test* poisons it by running pairs.

## 7. Determinism toolkit

When the loop itself is unstable because the code depends on ambient nondeterminism, pin each source. Pinning that requires a code seam (e.g. injecting `TimeProvider`) may itself reveal the bug — direct ambient dependency is a frequent root cause.

| Source | Pin it with |
|--------|-------------|
| Time | Inject `TimeProvider`; in tests use `FakeTimeProvider` (package `Microsoft.Extensions.TimeProvider.Testing`): `var time = new FakeTimeProvider(new DateTimeOffset(2026, 1, 15, 23, 59, 59, TimeSpan.Zero)); time.Advance(TimeSpan.FromSeconds(2));` — lets you sit exactly on midnight/DST boundaries. Direct `DateTime.Now` usage blocks this; note it as evidence. |
| Random | Seed it: construct the SUT with `new Random(1234)`, or temporarily replace `Random.Shared` call sites with a seeded instance (tagged). |
| Culture | Pin per-test: `CultureInfo.DefaultThreadCurrentCulture = CultureInfo.GetCultureInfo("de-DE");` — and to *reproduce* a CI/prod culture bug locally, set it to the server's culture, not yours. |
| Filesystem | Per-run isolated dir: `var dir = Directory.CreateTempSubdirectory("repro").FullName;` — never a shared path two runs can collide on. |
| Network | Stub the handler so the loop never touches the wire: |
| Ports | Never hardcode. `WebApplicationFactory` needs no port; raw listeners use port `0` (OS-assigned). |
| Test parallelism | Suspect cross-test interference? Disable and compare: `[assembly: CollectionBehavior(DisableTestParallelization = true)]` (xunit). If serial is green and parallel is red, shared state is the hypothesis. |

Network stub (complete):

```csharp
public sealed class StubHandler(HttpStatusCode status, string json) : HttpMessageHandler
{
    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken ct) =>
        Task.FromResult(new HttpResponseMessage(status)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        });
}

// var client = new HttpClient(new StubHandler(HttpStatusCode.OK, """{"rate":1.08}"""));
```

## 8. Human-in-the-loop last resort

Only when every recipe above is exhausted (bug needs hardware, a third-party UI, a production-only dataset). Make the human step as small as possible and script everything around it:

```powershell
Write-Host "1. Open the app, log in as auditor@test, open Reports > Q3."
Write-Host "2. Does the total show 150 (bug) or 100 (correct)?"
$answer = Read-Host "Enter 150 or 100"
if ($answer -eq "150") { exit 1 } else { exit 0 }
```

This is a slow, expensive loop — before settling for it, ask the user for artifacts that might enable a real one: the exact stack trace, structured logs, the failing HTTP request as curl, a `dotnet-dump collect` from the hung process, a database row export. One good artifact often upgrades you to recipe #1–#4.
