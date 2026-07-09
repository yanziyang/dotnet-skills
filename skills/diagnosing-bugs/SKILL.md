---
name: diagnosing-bugs
description: Systematically diagnose and fix bugs in C#/.NET projects (.NET 8–10, ASP.NET Core and class libraries) by building a red/green feedback loop first, then testing ranked hypotheses with targeted instrumentation, and finishing with a regression test. Use this skill whenever the user reports a bug, exception, crash, hang, deadlock, failing or flaky test, wrong output, data corruption, memory leak, or performance regression — or says something is "broken", "not working", "hanging", "slow", "weird", "works locally but fails in CI/prod", or "used to work" — even if they never say the word "debug".
metadata:
  origin: dotnet-skills
  targets: .NET 8, 9, and 10 (ASP.NET Core and class libraries)
---

# Diagnosing Bugs (.NET)

Diagnose hard bugs with a fixed sequence of phases, each with a completion gate. The core principle: **build the feedback loop before building a theory**. A feedback loop is one command that turns red while the bug exists and green when it is fixed. With that command, every hypothesis becomes cheap to test and impossible to fake; without it, you are guessing, and a plausible-sounding guess that "should fix it" is how debugging sessions go in circles. Build the right feedback loop and the bug is 90% fixed.

Work the phases in order. Do not skip ahead — each gate exists because the phase after it is unreliable without it.

| Phase | Output | Gate to pass before next phase |
|-------|--------|--------------------------------|
| 1. Feedback loop | One runnable red command | Command exists, you ran it, output shows the exact symptom |
| 2. Reproduce + minimize | Smallest scenario that still fails | Removing any remaining element makes it green |
| 3. Hypothesize | 3–5 ranked, falsifiable hypotheses | Each states a testable prediction |
| 4. Instrument | Evidence confirming ONE hypothesis | A probe result (not plausibility) confirmed it |
| 5. Fix + regression test | Green loop + committed failing-then-passing test | Test failed before the fix, passes after |
| 6. Cleanup + report | Clean tree + summary | Zero debug tags left, harnesses deleted, suite green |

## Phase 1 — Build the Feedback Loop

Spend disproportionate effort here; be creative. Pick the loop type from this table, then read [references/feedback-loops.md](references/feedback-loops.md) for the complete recipe — it has runnable code for every row. Match on the **first row that fits**:

| The bug lives in… | Loop to build | Recipe |
|-------------------|---------------|--------|
| Pure logic — a method/class you can call directly | Failing xUnit test in the existing test project | #1 |
| An ASP.NET Core endpoint's behavior (routing, filters, DI, serialization) | `WebApplicationFactory` integration test | #2 |
| Behavior that needs the real running server or config | Script (curl / `Invoke-RestMethod`) against `dotnet run`, asserting on the response | #3 |
| A console app, worker service, or code with no test project | Throwaway console harness referencing the project | #4 |
| A regression — "it used to work" | `git bisect run` driving one of the loops above | #5 |
| An intermittent/flaky failure | Amplification loop (run 100×, add stress) around one of the loops above | #6 |
| Nondeterminism itself (time, random, culture, parallelism) | Determinism toolkit — pin the source, then loop normally | #7 |
| Something you cannot reproduce at all | Stop and ask the user (see fallback below) | #8 |

A loop qualifies only when **all four** hold — check them explicitly:

- [ ] **Red-capable**: you ran it and pasted output showing the user's *exact* symptom (same exception type and message, same wrong value — not a nearby different failure).
- [ ] **Deterministic**: same verdict every run. For flaky bugs, use recipe #6 to raise the reproduction rate to roughly 50% or better first — a loop that fails 1 run in 30 cannot distinguish hypotheses.
- [ ] **Fast**: seconds, not minutes. A 2-second deterministic loop is a debugging superpower; a 30-second flaky one is barely better than none. Cut setup, scope the test filter, use SQLite in-memory instead of a real database where the bug allows it.
- [ ] **Unattended**: it runs without a human clicking anything, and its exit code or output tells you red/green.

**Fallback — when you cannot build a loop.** Do not silently continue. List the loop types you attempted and why each failed, then ask the user for what would unblock you: the exact exception with full stack trace, application logs around the failure, the failing request (method, URL, headers, body), `appsettings.*.json` plus environment name, a database snapshot or the specific row, a memory dump (`dotnet-dump collect -p <pid>`), or permission to add temporary instrumentation to the target environment. **Do not proceed to hypotheses without a loop** — analysis without a red/green signal produces plausible fixes, not verified ones.

**Anti-pattern check**: if you catch yourself reading code to figure out *why* the bug happens before this command exists, stop and return here. Reading code to *choose a loop type* is fine; theorizing is not yet.

## Phase 2 — Reproduce and Minimize

**Reproduce**: run the loop and confirm the failure is the user's bug. Quote the user's reported symptom and your loop's output next to each other. If they differ (different exception, different endpoint, different value), you found a *different* bug — note it, but keep hunting for the reported one.

**Minimize**: shrink the red scenario one element at a time — input fields, request headers, seeded rows, config values, middleware, steps — re-running the loop after each removal. If it stays red, the element was noise; keep it deleted. If it turns green, the element is load-bearing; put it back and note it, because load-bearing elements are evidence about the cause.

Gate: every element still in the repro is load-bearing. A minimal repro shrinks the hypothesis space in Phase 3 and becomes the regression test in Phase 5 — the effort pays for itself twice.

## Phase 3 — Hypothesize

Write down **3–5 hypotheses before testing any of them**. Generating several up front is the defense against anchoring — committing to the first plausible idea and bending every later observation to fit it.

Open [references/common-causes.md](references/common-causes.md) and find the section matching your symptom fingerprint (hangs, flaky, works-locally-fails-in-CI, wrong/stale data, a specific exception, slow). It maps .NET symptoms to their statistically likely causes with ready-made predictions — use it to generate candidates, then add any suggested by your minimized repro's load-bearing elements.

Each hypothesis must be **falsifiable** — state the prediction it makes:

> **H1 (likely)**: The total is wrong because `GetOrders` returns tracked entities cached by a previous query in the same `DbContext`.
> **Prediction**: adding `.AsNoTracking()` to that one query makes the loop green; and logging the entity's `Id` and reference hash at both call sites shows the same instance.

A hypothesis with no prediction ("maybe it's a threading thing") is not testable — sharpen it or discard it. Rank the list by likelihood. If the user is present, show them the ranked list — they often rule candidates out instantly with domain knowledge ("we don't use lazy loading"). If not, proceed with your ranking.

## Phase 4 — Instrument and Test Hypotheses

Test hypotheses in rank order. Each probe must map to a specific prediction from Phase 3, and you change **one variable at a time** — re-run the loop after every change so you know exactly which change moved the needle.

The probe ladder, cheapest first (details and code in [references/instrumentation.md](references/instrumentation.md) — read it before adding any instrumentation):

1. **Vary the input or config and re-run the loop** — no code changes. Different culture, one row instead of many, tracking on/off, a config flag flipped.
2. **Targeted, tagged log lines** at the exact boundaries that distinguish hypotheses — the value going *into* the suspect call and *out of* it. Not "log everything and grep".
3. **.NET diagnostic CLI tools** for what logs can't see: `dotnet-counters` (thread pool, GC), `dotnet-dump`/`dotnet-stack` (hangs — stack of every thread), `dotnet-trace` (CPU time), EF Core `LogTo` (the actual SQL).

**Tagging discipline**: at the start of Phase 4 pick a random 4-hex session tag (e.g. `a4f2`) and prefix every debug line with it — `[DEBUG-a4f2]`. Every temporary code comment gets `// DEBUG-a4f2` too. This makes Phase 6 cleanup a single grep; untagged debug logs are the ones that ship to production.

**Performance regressions are different**: never diagnose them from reading code or adding logs — both mislead. Measure a baseline first (timing harness or `dotnet-counters`), then bisect the pipeline by timing stages until the slow stage is cornered. The perf workflow is in the instrumentation reference. Measure first, fix second.

**If every hypothesis is falsified**: that is progress — the evidence you gathered rules out whole categories. Return to Phase 3 with the new evidence and generate the next batch. Do not start making speculative code changes to "see if it helps"; that destroys the loop's meaning.

## Phase 5 — Fix and Regression Test

Confirmed cause in hand, write the regression test **before** the fix:

1. Convert the minimized repro into a permanent test at the correct seam:
   - Logic bug → unit test in the existing test project.
   - Endpoint/DI/serialization bug → `WebApplicationFactory` test.
   - Concurrency bug → a test that provokes the race deterministically (recipe #6 shows how); if it can only be made probabilistic, loop it enough to be reliable and say so in the test comment.
   - **No correct seam exists** (the bug needs a caller chain or environment no test can exercise) → do not write a shallow test that passes for the wrong reason; document the missing seam in the final report instead.
2. Run it. **Watch it fail** — a regression test you never saw red proves nothing.
3. Apply the fix. Fix the **root cause**, not the symptom: wrapping the crash site in `try/catch`, adding a null-check that hides where the null came from, or a `Thread.Sleep` that hides a race are symptom patches that resurface later.
4. Watch the test pass, then re-run the **original, un-minimized Phase 1 loop** — the fix must cure the user's actual scenario, not just the minimized one.
5. Run the full test suite (`dotnet test`) to catch collateral damage.

## Phase 6 — Clean Up and Report

Checklist — all boxes, no exceptions:

- [ ] `grep -rn "DEBUG-<tag>"` across the repo returns zero hits (search `git status` untracked files too).
- [ ] Throwaway harness projects/scripts deleted.
- [ ] Debug-only config reverted: log levels, `EnableSensitiveDataLogging`, `appsettings` edits, commented-out code restored.
- [ ] Regression test in place and passing; full suite green.

Then report in chat, using exactly this structure:

> **Bug**: one sentence — the symptom as the user experienced it.
> **Root cause**: what was actually wrong, with `file:line`, and which hypothesis it was.
> **Fix**: what changed and why that addresses the root cause.
> **Regression test**: test name and location; confirmation you saw it fail before the fix.
> **Prevention**: what would have stopped this bug from existing — a missing test seam, a type that allows invalid states, a hidden coupling.

If the prevention answer implicates architecture (no seam to test at, tangled callers, ambient state), state it and suggest the `improve-codebase-architecture` skill as a follow-up — after the fix is in, never instead of it.

## Rules

- **No theory before a loop.** The red command exists and has been run before any hypothesis is written.
- **One variable at a time.** Every probe changes one thing; the loop is re-run after each.
- **Evidence over plausibility.** A hypothesis is confirmed by a probe result you can quote, never by "that looks like it would cause this".
- **Falsified is progress.** Ruling a hypothesis out is a win; record it and move down the list.
- **Root cause, not symptom.** No catch-and-ignore, no papering null-checks, no sleep-until-it-passes.
- **Never claim fixed without red→green.** The claim "this fixes it" requires having watched the loop go from red to green on that exact change.
- **Leave no trace.** Tagged instrumentation, harnesses, and config tweaks all go before the report.
- **Ask when stuck.** After genuine loop-building attempts fail, stop and request artifacts — silent guessing wastes everyone's time.
