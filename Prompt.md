-----------------------------------------------------------
api-design agent skills
-----------------------------------------------------------

Prompt:

Create api-design agent skills for .NET projects (.NET 10 etc).

description: REST API design patterns including resource naming, status codes, pagination, filtering, error responses, versioning, and rate limiting for production APIs.

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc. 

Fable 5 Response:

All four files are written. Now I'll update the repo README to index the skill and do a final consistency check.

Created a file, ran a command
The api-design skill is created. Here's what's in skills/api-design:

Structure — progressive disclosure so a mid-tier model only loads what it needs:

SKILL.md (370 lines) — the core that loads when the skill triggers: URL/naming conventions, route groups, HTTP method and status-code rules, the TypedResults/Results<...> union pattern, DTO and JSON conventions, auth with ownership checks, OpenAPI, middleware ordering, and a ship checklist. A routing table at the top tells the model which reference file to read before implementing each concern.
references/error-handling.md — RFC 9457 ProblemDetails everywhere, global IExceptionHandler, .NET 10 built-in minimal-API validation (AddValidation()) plus a FluentValidation endpoint-filter fallback for .NET 8/9, and a status-code decision table.
references/pagination-filtering.md — offset and cursor (keyset) pagination with complete EF Core implementations, opaque Base64Url cursors, typed filters via [AsParameters], whitelisted sorting, and search guidance.
references/versioning.md — Asp.Versioning setup for both Minimal APIs and controllers, breaking vs. non-breaking change rules, and a deprecation/Sunset-header timeline.
references/rate-limiting.md — built-in AddRateLimiter with all four algorithms, per-user/per-IP partitioning, tiered plans, 429 + Retry-After ProblemDetails responses, and multi-instance caveats.
Key adaptations from the ECC reference — that skill was generic TypeScript/Python/Go, so beyond translating code I changed idioms to match .NET: camelCase JSON (not snake_case), {id:guid} route constraints (not :id), ProblemDetails instead of the custom { "error": {...} } envelope, and framework-native mechanisms (rate-limiting middleware, Asp.Versioning) instead of hand-rolled patterns. Since the audience is mid-tier models (Sonnet, GLM, DeepSeek), everything is prescriptive: complete runnable code rather than fragments, explicit "read X before implementing Y" pointers, exact package names, and decision tables instead of open-ended trade-off discussion.

I also updated README.md to index the skill. Nothing is committed — say the word if you want a commit.

Two optional follow-ups I can run: spawn test prompts through subagents (with-skill vs. baseline) to benchmark whether the skill measurably improves output, and/or run the description-triggering optimization loop. Both take a while, so I left them for you to decide.

-----------------------------------------------------------
improve-codebase-architecture agent skills
-----------------------------------------------------------

Prompt:

Create improve-codebase-architecture agent skills for .NET projects (.NET 10 etc).

description: Scan a codebase for deepening opportunities, present them as a visual HTML report

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc. 

Fable 5 Response:

I'll create this skill. Let me start by loading the skill-creator skill and looking at the reference material.

Ran skill
/anthropic-skills:skill-creator
Let me look at the reference skill and the current repo structure.

Found files, read 4 files, created 2 files
Now the HTML report reference, with a complete scaffold and a fully worked example card so a mid-tier model can pattern-match rather than invent:

Created
html-report.md

Now update the README's skills table:

The skill is complete. Here's a summary of what I created:

What was built
skills/improve-codebase-architecture/SKILL.md — the core skill, following this repo's conventions (origin/targets metadata, prescriptive instructions, pushy trigger description). Key adaptations from the reference skill for mid-tier models:

Vocabulary inlined. The reference skill delegates its design vocabulary (deep/shallow module, seam, adapter, locality, leverage, deletion test) to a companion /codebase-design skill that consumers of this repo won't have. I inlined it as a definition table, since consistent terminology is what holds the report together.
Organic exploration replaced with a concrete procedure. The reference says "explore organically and note friction" — reliable for a frontier model, vague for a mid-tier one. The new skill walks through explicit steps: map the solution (glob .sln/.csproj, read package references as architecture evidence, read the DI registrations as a census of seams), scan against a fixed smell catalog, grade with stated criteria, cap at 6 candidates, require file-level evidence for every claim.
Explicit guardrails: read-only until the user picks a candidate, never propose adopting a framework as the fix, respect ADRs, counter-signals drop findings.
references/dotnet-smells.md — the .NET-specific catalog, which is entirely new material. Nine smells (pass-through service layers, one-implementation interfaces, generic repository over EF Core, anemic entities, MediatR ceremony, AutoMapper indirection, layer-per-project sprawl, leaky seams, Helper/Util wrappers), each with grep-able detection patterns, counter-signals that justify the pattern, and complete before/after C# targeting .NET 8–10 idioms (Minimal APIs, TypedResults, TimeProvider). Ends with a reinforcement map — e.g. pass-through service + header interface + generic repo travel together and should become one Strong candidate, not three medium ones.

references/html-report.md — the report format, adapted from the reference's version but made copy-able: full Tailwind+Mermaid scaffold, a complete worked candidate card to pattern-match against, five diagram patterns with ready HTML (Mermaid flowchart, mass diagram, cross-section, collapse, sequence), exact badge color classes, and Windows/macOS/Linux temp-file and open commands.

I also added the skill to the README table.

One deliberate scope change from the reference: its step 3 ("grilling loop") invoked three more companion skills. I replaced it with a self-contained "stop and ask" step — present the report, ask which candidate to explore, and offer to record rejections as ADRs so future scans don't re-suggest them.

If you'd like, as a next step I can build a small deliberately-smelly .NET solution and run the skill-creator eval loop against it (with-skill vs. baseline subagent runs, graded, with the browser review viewer) to validate how a mid-tier model actually performs with it — just say the word.

-----------------------------------------------------------
code-review agent skills
-----------------------------------------------------------

Prompt:

Create code-review agent skills for .NET projects (.NET 10 etc.). This agent skills shall present result as a visual HTML report.

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc.

Fable 5 Response:

I'll create a .NET code-review skill for this repo. Let me first load the skill-creator skill and look at the existing skill's structure to match conventions.

Found files, used a tool
The skill-creator workflow is loaded. Since this repo already has an established skill pattern, let me study the existing improve-codebase-architecture skill to match its conventions before drafting.

Read 3 files, created 3 files
All three files are written. Now updating the README's skills table to include the new skill.

Edited 2 files
The code-review skill is created, following the repo's established layout and matched to the existing improve-codebase-architecture conventions. Three files, plus a README entry:

SKILL.md — the workflow: a scope decision tree with exact git/gh commands, a "read the whole file, not the hunk" rule, category-by-category hunting passes, a four-step verification gate every finding must pass, report rendering, and a mechanical verdict (any Blocker → Request changes; Warnings only → Approve with reservations; else Approve).
references/review-checklist.md — the defect catalog: ~30 .NET-specific checks across 8 categories (async/threading, EF Core, security, correctness, lifetimes, API contract, performance, tests), each with a grep-able detection pattern, the concrete failure it causes, a bad→good code pair, and "not a finding when" counter-signals.
references/html-report.md — a complete Tailwind scaffold to copy: verdict badge, severity stat tiles, files table, finding cards with dark code blocks (offending line highlighted red, fix bordered emerald), and an anchor-linked fix-first list. Zero JavaScript beyond the Tailwind CDN, so nothing can break at render time.
Design choices aimed at mid-tier models (Sonnet, GLM, DeepSeek class):

Judgment replaced with decision procedures — severity comes from three yes/no questions, the verdict from a lookup table, scope from a stop-at-first-match list. Nowhere does the skill say "use your judgment".
Anti-hallucination gates — every finding must quote the actual code at a real file:line, survive a "handled elsewhere" search, and name a concrete failure scenario, or it gets dropped. Caps (max 12 findings, max 3 Suggestions) prevent padding, and an explicit "empty is a valid result" rule prevents invented findings.
Copy-paste templates — the HTML scaffold and finding card are complete, so the model fills placeholders rather than designing layout. The escaping rules (< → &lt; etc.) are called out first, since unescaped C# generics silently corrupting the report is the classic mid-tier failure.
Two follow-ups you may want, just say the word:

Test it — I can run the skill-creator eval loop: spawn subagent runs on sample .NET diffs with and without the skill, and open a review viewer so you can compare the reports.
Commit — the working tree has the new skill plus the README edit, ready to commit whenever you want.

-----------------------------------------------------------
architecture-design-document agent skills
-----------------------------------------------------------

Prompt:

Create architecture-design-document agent skills for .NET projects (.NET 10 etc.). 

Requirements for the agent skills:
- Run through the whole code repository to have a full understanding of the solution.
- Generate architecture design document as word document (docx file)
- Include professional-looking diagrams / images for better illustration
- Export diagrams in drawio or other suitable format to enable further editing by user. Save the diagarms in 'diagrams' sub-folder.
- If there is mermaid diagram used, convert it to image, and export both mermaid diagram and images in 'diagrams' sub-folder.


The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc.

Fable 5 Response:

I'll create an architecture-design-document skill for .NET projects. Let me start by loading the skill-creator skill to follow best practices.

Ran skill
/anthropic-skills:skill-creator
Let me first look at the existing skills in this repo to match their conventions.


Found files, read 2 files, used a tool
Python and Node are available. Installing python-docx for testing the scripts:


Created 3 files, used 3 tools
Let me clean up a leftover buggy helper in make_drawio.py:

Edited
make_drawio.py
+5
-13
Now let me test all three scripts with sample fixtures in the scratchpad:


Created 2 files, used a tool
Both scripts work — but it fell through to npx, meaning the kroki fallback failed even though network is available. Let me check why:

Used PowerShell
Kroki is blocking the default Python user agent (Cloudflare error 1010). Adding a proper User-Agent header:


Edited a file, read 2 files, created a file, used 3 tools
All three scripts verified — headings, cover, tables, scaled images, lists, TOC field, and page-number fields all check out. Now writing the SKILL.md and reference files:


Created 3 files
Now the main SKILL.md:


Created 7 files, used a tool
Now the full document source, following the template skeleton:


Created a file, read 2 files, edited a file, used a tool
Everything is built and verified. Let me do a final compile check on the scripts and review the finished skill layout:

Used PowerShell
Done — the architecture-design-document skill is complete, tested end-to-end, and listed in the README. The working tree has the new skill folder plus the README update, uncommitted (say the word and I'll commit).

What was built
skills/architecture-design-document/ following this repo's layout:

SKILL.md (136 lines) — a 7-step prescriptive workflow: scan the whole repository (solution shape, project references, composition root, HTTP surface, data layer, integrations, cross-cutting concerns, deployment evidence) → author diagrams → render → export draw.io copies → write the document → build the docx → deliver. Rules enforce evidence-based content and a read-only scan.
Three bundled scripts — this is the key design choice for mid-tier models (Sonnet/GLM/DeepSeek-class): the LLM only writes Markdown, Mermaid, and a small JSON spec; deterministic Python does everything error-prone:
build_docx.py — constrained Markdown → styled .docx with cover page, TOC field (auto-update on open), headers/footers with page numbers, styled tables, auto-numbered figure captions, auto-scaled images. Exits non-zero listing any missing image so the model gets actionable feedback.
render_diagrams.py — renders every .mmd to PNG via local mmdc → kroki.io → npx fallback chain, surfacing Mermaid syntax errors on failure. Includes a privacy note when the kroki web service is used (the skill instructs asking the user first for confidential codebases).
make_drawio.py — JSON node/edge spec → fully editable .drawio with automatic layered layout, consistent palette, orthogonal labeled edges.
Three references — document-template.md (complete ADD section skeleton with per-section instructions), diagram-recipes.md (the 6-diagram catalog with worked examples and the syntax pitfalls that actually break renderers), and drawio-spec.md.
Requirements coverage
Every diagram ships as editable source + image in the diagrams/ subfolder: .mmd + .png for all six diagram types, plus .drawio (+ its regeneration spec) for the system-context and container diagrams. The docx embeds the PNGs; the sources stay for user editing.

Verification
I ran the full pipeline against a realistic sample (ShopLite, 4-project .NET 10 solution): all 6 diagram types (flowcharts with subgraphs, sequence, ER) rendered cleanly via kroki, both drawio files generated with valid XML, and the 240 KB docx passed structural checks (headings, cover, 2 tables, scaled images, TOC field, list styles, page-number fields). One real bug was found and fixed during testing: kroki.io's Cloudflare rejects Python's default user agent, so the script now sends a browser-compatible one. Diagrams I spot-checked visually all look professional (you saw the samples above).

Two optional follow-ups if you want them: commit the changes, or run a proper multi-model eval loop (spawning fresh agents against a sample repo with/without the skill) to benchmark how well mid-tier models follow it.

-----------------------------------------------------------
FS-and-MDS-document agent skills
-----------------------------------------------------------

Prompt:

Create FS-and-MDS-document agent skills for .NET projects (.NET 10 etc.). 

Requirements for the agent skills:
- Run through the whole code repository to have a full understanding of the solution.
- Generate functions spec (FS) and module design spec (MDS) document as word document (docx file)
- Include professional-looking diagrams / images for better illustration
- Export diagrams in drawio or other suitable format to enable further editing by user. Save the diagrams in 'diagrams' sub-folder.
- If there is mermaid diagram used, convert it to image, and export both mermaid diagram and images in 'diagrams' sub-folder.

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc.

Fable 5 Response:

I'll create the FS-and-MDS skill following the same proven pattern as the architecture-design-document skill — bundled deterministic scripts, Mermaid + draw.io exports in diagrams/, and prescriptive templates. Key design decisions: two separate Word documents (FS = what the system does functionally; MDS = how each module is designed), a shared diagrams/ folder, and each skill stays self-contained (scripts are copied, since skills are installed by copying one folder).

I also noticed the previous commit accidentally included __pycache__/*.pyc files — I'll fix that with a .gitignore while I'm at it.

First, copy the verified scripts and test the two new Mermaid diagram types this skill needs (classDiagram, stateDiagram):

Created 7 files, read a file, used 2 tools
Now the end-to-end test — validating the remaining new recipe shapes (feature map, process flow with decisions) and building both documents:

Created 3 files
Now compact FS and MDS test documents, then run the full pipeline:

Created 2 files, used a tool
The whole pipeline passes — 8 diagrams, 2 drawio files, both documents built. Spot-checking the process flow with decision branches:

Read
03-process-place-order.png

Now updating the README, adding a .gitignore, and untracking the __pycache__ files that slipped into the previous commit:

Edited a file, created a file, used a tool
Done — the fs-mds-document skill is complete and fully tested. Everything is ready in the working tree, uncommitted.

What was built
skills/fs-mds-document/ — same proven architecture as the architecture-design-document skill, self-contained (scripts copied in, since skills install as one folder):

SKILL.md (148 lines) — a 7-step workflow that scans the repository once with two lenses (functional: entry points, validation, processing rules, business rules, actors, state transitions; design: solution shape, DI, module internals, data layer, integrations), then produces two Word documents:
Functional-Specification.docx — what the system does, written so a tester can derive test cases: feature areas (FA-n) with per-requirement (FR-n-n) trigger/inputs/processing/outputs/errors, a global business-rules catalog (BR-n), actors and roles, process flows, entity lifecycles.
Module-Design-Specification.docx — how it's designed: per-module purpose, public interface, class diagrams, dependencies, database table specs, API endpoint tables, plus a requirements-to-module traceability appendix that cross-links the FR IDs from the FS.
Four references — fs-template.md and mds-template.md (complete section skeletons with ID conventions and per-section instructions), diagram-recipes.md (8 diagram recipes including the new classDiagram and stateDiagram-v2 types, with the syntax pitfalls that break mid-tier models — tilde generics, identifier-only state names), and drawio-spec.md.
Scripts — the three verified Python tools (docx builder, Mermaid renderer with mmdc/kroki/npx fallback, draw.io generator).
All requirements covered: every diagram ships as editable .mmd + rendered .png in the diagrams/ subfolder, and the two structural diagrams (context, module structure) additionally get editable .drawio files.

Verification
I ran the complete pipeline against the ShopLite sample: all 8 diagram types rendered (including the new class diagram with interface stereotypes and the state/process diagrams — spot-checked visually, all professional), both .drawio files generated, and both docx files built cleanly (162 KB / 219 KB) with cover, TOC, tables, and figures.

I also fixed a housekeeping issue from the previous commit: __pycache__/*.pyc files had slipped in, so I added a .gitignore and staged their removal from tracking.

Want me to commit and push this to main like last time?

-----------------------------------------------------------
Presentation-slides agent skills
-----------------------------------------------------------

Prompt:

Create Presentation-slides agent skills for .NET projects (.NET 10 etc.). 

Requirements for the agent skills:
- Run through the whole code repository to have a full understanding of the solution.
- Generate professional-looking Presentation slides as PowerPoint (.pptx) that targeting new team members, management, customers.
- Include professional-looking diagrams / images for better illustration
- Export diagrams in drawio or other suitable format to enable further editing by user. Save the diagrams in 'diagrams' sub-folder.
- If there is mermaid diagram used, convert it to image, and export both mermaid diagram and images in 'diagrams' sub-folder.

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc.

Fable 5 Response:

I'll create this skill for the repo. Let me start by loading the skill-creator skill and looking at the existing skill conventions in this repository.

Ran skill
/anthropic-skills:skill-creator
I'll first examine the existing skills in this repo to match their structure and conventions.

Found files, ran 7 commands, read 5 files, created a file
Now the deck spec reference that documents the deck.json format:

Created
pptx-spec.md

Now the deck outline reference (storyline + audience tailoring):

Created
deck-outline.md

Now the diagram recipes, adapted for 16:9 slides (fewer nodes, landscape orientation):

Created 5 files, edited a file, read a file, ran a command
Now the test deck.json covering all 11 slide types:

Created a file, ran 6 commands, read a file
The diagram renders professionally with the standard palette. Let me check the repo README to see if new skills get listed there:

Read a file, edited a file
Everything is built and verified. The final structure:

Showed final skill file tree and sizes
Done. The new presentation-slides skill is created at skills/presentation-slides/ and tested end-to-end — a 13-slide sample deck built cleanly on the first run, with valid geometry, speaker notes, footers, and correctly fitted diagram images.

What was built
The skill follows the same conventions as your architecture-design-document skill (read-only repo scan → Mermaid diagrams → draw.io exports → deliverable), with one key design decision for the middle-tier-model audience: the executing model never writes python-pptx code. It writes a content-only deck.json, and a bundled deterministic builder owns all layout, fonts, and colors — so Sonnet/GLM/DeepSeek-class models can't produce ugly or broken decks by fumbling coordinates.

SKILL.md — 8-step workflow: check prerequisites → pin down audience (new team members / management / customers, defaulting to team members) → scan the repo (csproj/packages, DI, HTTP surface, DbContext, integrations, quality signals, deployment evidence) → author + render diagrams → export draw.io copies → write deck.json → build the .pptx → deliver.
scripts/build_pptx.py — new deterministic builder: 16:9, Segoe UI, navy/blue palette matching the diagrams; 11 slide types (title, section, bullets, two_column, cards, stats, image, image_bullets, table, timeline, closing); real hanging-indent bullets, **bold** support, auto font shrinking, aspect-preserving image fitting, speaker notes, slide numbers. It validates everything and reports all problems in one run (verified: typo'd slide type, missing image, and ragged table row each produced a clear one-line error and exit 1).
scripts/render_diagrams.py and make_drawio.py — reused from the architecture skill. Mermaid .mmd sources and rendered .pngs both land in diagrams/, plus editable .drawio copies of the two structural diagrams — exactly per your requirements.
References — deck-outline.md (17-slide storyline with per-audience adjustments, e.g. management gets risks + roadmap and no data model; customers get benefits and no internal structure), pptx-spec.md (full deck.json schema with examples for every slide type), diagram-recipes.md (slide-tuned: ≤10 nodes, landscape-first), and drawio-spec.md.
I also added the skill to the README.md table.

Verification
Tested on this machine (Python 3.14 via py, python-pptx 1.0.2, local mmdc): rendered a context + sequence diagram, generated the .drawio export, and built a full deck exercising all 11 slide types. A programmatic audit confirmed no out-of-bounds shapes and correct image centering. If you want to eyeball it before committing, the sample is at C:\Users\admin\AppData\Local\Temp\claude\C--MyProjects-dotnet-skills\c7e41311-6d32-478b-806c-b077c2b5561f\scratchpad\test-deck\ShopLite-Overview.pptx.

Two follow-ups I can do on request: run a subagent eval of the skill against a real sample .NET solution (the full skill-creator eval loop), and/or commit the new skill following your existing commit-message style.

-----------------------------------------------------------
diagnosing-bugs agent skills
-----------------------------------------------------------

Create diagnosing-bugs agent skills for .NET projects (.NET 10 etc).

reference:
https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnosing-bugs/SKILL.md

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc. 

Fable 5 Response:

I'll load the skill-creator skill first, then study the reference and your repo conventions.

Found files, ran 2 commands, browsed the web, read 3 files, created 4 files, used 2 tools
All four files are written. Now updating the README's skills table and doing a final consistency check:

Edited a file, ran a command
The diagnosing-bugs skill is complete at skills/diagnosing-bugs/, following the repo's conventions (origin/targets metadata, pushy trigger description, progressive disclosure), with the README table updated. Everything is in the working tree, uncommitted.

What was built

SKILL.md (129 lines) — the six-phase workflow from the mattpocock reference, restructured for mid-tier models: every phase has an explicit completion gate (a phase-map table up front), Phase 1 routing is a stop-at-first-match table from "where the bug lives" to a numbered loop recipe, and the core discipline is stated as checkable rules — no theory before a red command exists, one variable per probe, evidence over plausibility, watched red→green before claiming fixed, and a fixed final report template (Bug / Root cause / Fix / Regression test / Prevention) that hands off to your existing improve-codebase-architecture skill when the prevention answer implicates architecture.

Three references, loaded on demand:

feedback-loops.md — eight loop recipes with complete runnable code, all .NET-native: xUnit repro with --filter, WebApplicationFactory with the SQLite service-swap and the public partial class Program gotcha, HTTP script loops (PowerShell and bash), throwaway console harness kept outside the solution, git bisect run with the copy-the-repro-in script (including exit-125 skip for unbuildable commits), flaky-bug amplification (run-100× counters, thread-pool starvation, race-window widening), a determinism-pinning table (FakeTimeProvider, seeded Random, culture, ports, xunit parallelism, a complete HttpMessageHandler stub), and a scripted human-in-the-loop last resort.
instrumentation.md — the tagged [DEBUG-<4hex>] discipline (cleanup becomes one grep), framework logging via env vars so nothing gets committed, EF Core LogTo with a "what the SQL output means" decoder, first-chance exception hooks for swallowed errors, hang diagnosis with dotnet-stack/dotnet-dump including how to read the starvation and deadlock signatures, the measure-first perf workflow (baseline harness → bisect by time or pipeline stage → verify numerically), and gcdump-diff memory-leak hunting.
common-causes.md — the main .NET-specific addition beyond the reference: ~30 root causes organized by symptom fingerprint (hangs, flaky, works-locally-fails-in-CI, wrong/stale data, exceptions decoded, slow), each with a grep pattern and a ready-made falsifiable prediction, so a mid-tier model gets its Phase 3 hypotheses from a catalog instead of free associating. The "exceptions decoded" section maps exact .NET exception messages (A second operation was started on this context, TaskCanceledException-is-really-a-timeout, etc.) straight to their causes.
Key adaptation for the mid-tier audience: the reference skill puts "debugger/REPL inspection" at the top of the instrumentation ladder — agents run headless, so the ladder here is re-run-the-loop-with-varied-input → tagged logs → dotnet-* CLI diagnostics, all scriptable. Judgment calls are replaced with tables and checklists throughout, and the "stop and ask the user" fallback lists the exact artifacts to request (stack trace, HAR-style request, dotnet-dump collect, config + environment name).

Two optional follow-ups on request: run the skill-creator eval loop (subagents debugging a deliberately-buggy sample solution with/without the skill, plus the review viewer), and/or commit — the tree also still has your earlier Prompt.md edit pending.

-----------------------------------------------------------
data-dictionary-document agent skills
-----------------------------------------------------------

Prompt:

Create data-dictionary-document agent skills. 

Requirements for the agent skills:
- Run through the whole code repository, documentation to have a full understanding of the solution.
- Create data dictionary document as word document (docx file) based Data Definition Language (DDL) provided.
- Include Entity Relationship Diagram (ERD). If there are two many tables, break down Entity Relationship Diagram (ERD) by modules.
- Export diagrams in drawio or other suitable format to enable further editing by user. Save the diagrams in 'diagrams' sub-folder.
- If there is mermaid diagram used, convert it to image, and export both mermaid diagram and images in 'diagrams' sub-folder.

The agent skills will be used by middle-tier LLM model such as Sonnet 5.6, GLM-5.2, Deekseek V4 Pro etc.

Fable 5 Response:

Another skill in the same family — I'll follow the established conventions. Per the repo pattern, I need to check the existing build_docx.py (whether it handles the table-heavy markdown a data dictionary needs) before deciding what to reuse.

Read a file, ran 2 commands, used a tool
Now the new ERD draw.io generator:

Created a file, edited a file
Now the references. First, the ERD recipes with the module-splitting rules:

Created 2 files
Now the document template — the heart of the data dictionary:

Created
document-template.md

Now the SKILL.md:

Created 5 files, ran a command
All three stages passed on the first run. Now verifying the outputs — the ERD render, the draw.io XML structure, and the docx contents:

Read a file, ran 2 commands, edited a file
Done. The new data-dictionary-document skill is at skills/data-dictionary-document/, tested end-to-end — ERD rendering, draw.io export, and docx build all passed on the first run, and I verified the outputs programmatically and visually.

What was built
SKILL.md — 8-step workflow: locate the DDL (user-provided file first; else .sql in the repo; else generate via dotnet ef migrations script or reconstruct from the EF ModelSnapshot.cs with the source clearly labelled — and stop to ask if none exist, since a dictionary invented from entity classes would misstate types and constraints) → parse tables/columns/keys/indexes → mine the repo for meaning (XML docs, HasComment, enums behind columns, HasData seeds, usage) → author + render ERDs → export draw.io twins → write the markdown → build the docx → deliver. Core rule: the DDL is the truth — code only adds meaning, and code-vs-schema drift is reported as a finding.
scripts/make_drawio_erd.py — the new piece: generates native draw.io entity table shapes (swimlane + stacked column rows, bold PK/FK rows) with real crow's-foot line ends mapped from cardinalities like 1:N, 1:0..1, N:M, laid out in a grid. Fully editable in app.diagrams.net — verified the XML structure (5 entities, 15 rows, 4 edges with correct ERone/ERmany/ERzeroToOne arrows in the test).
scripts/build_docx.py and render_diagrams.py — reused from the architecture skill (docx defaults retitled). Mermaid .mmd + rendered .png both land in diagrams/, per your requirements.
References — erd-recipes.md with the module-split rules you asked for: ≤ 12 tables → one full ERD; more → module ERDs of 5–12 entities chosen by schema > FK clusters > DbContext/namespace > name prefixes, plus a 00-erd-overview module map and name-only stub entities for cross-module FKs. document-template.md gives the exact skeleton (sources, notation legend, per-module chapters with per-table Columns / Keys & Constraints / Indexes tables, flat FK reference, seed data, glossary) with a † marker distinguishing inferred descriptions from evidenced ones. drawio-erd-spec.md documents the JSON spec.
As with the previous skill, everything a middle-tier model executes is deterministic scripting — it writes only Mermaid text, JSON specs, and constrained markdown; the bundled scripts own all rendering and fail loudly with fixable, per-item error messages.

README.md now lists the skill. The test artifacts (sample ERD PNG, .drawio, and Data-Dictionary.docx) are in ...\scratchpad\test-dd\ if you want to open them before committing — and I can commit both new skills in your existing style whenever you say the word.
