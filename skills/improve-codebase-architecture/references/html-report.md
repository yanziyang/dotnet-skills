# HTML Report Format

The review is one self-contained HTML file written to the OS temp directory. Tailwind (styling) and Mermaid (graph diagrams) load from CDNs; there is no other JavaScript. Follow this document closely — copy the scaffold and the card template, then fill in content. Do not invent a different layout.

## Contents

1. [File mechanics](#file-mechanics)
2. [Scaffold](#scaffold)
3. [Report structure](#report-structure)
4. [Candidate card template](#candidate-card-template)
5. [Diagram patterns](#diagram-patterns)
6. [Badges and colors](#badges-and-colors)
7. [Tone and wording](#tone-and-wording)

## File mechanics

- Path: `<tempdir>/architecture-review-<yyyyMMdd-HHmmss>.html`. Temp dir: `$env:TEMP` on Windows, `$TMPDIR` falling back to `/tmp` on macOS/Linux. Never write into the repository.
- Open after writing: `Start-Process <path>` (Windows PowerShell), `open <path>` (macOS), `xdg-open <path>` (Linux).
- Always tell the user the absolute path in chat — auto-open can fail, and CDN assets need a network connection.

## Scaffold

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Architecture review — {{solution name}}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
  </script>
</head>
<body class="bg-stone-50 text-slate-900 font-sans">
  <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">

    <header class="space-y-2">
      <h1 class="text-3xl font-serif font-semibold">Architecture review — {{solution name}}</h1>
      <p class="text-sm text-slate-500">{{date}} · {{N}} projects scanned · {{M}} candidates</p>
      <div class="flex gap-4 text-xs text-slate-500 pt-2">
        <span><span class="inline-block w-3 h-3 border-2 border-slate-700 align-middle mr-1"></span>module</span>
        <span><span class="inline-block w-3 h-3 border-2 border-slate-400 border-dashed align-middle mr-1"></span>seam</span>
        <span><span class="inline-block w-3 h-3 bg-red-500 align-middle mr-1"></span>leak</span>
        <span><span class="inline-block w-3 h-3 bg-slate-800 align-middle mr-1"></span>deep module</span>
      </div>
    </header>

    <section id="solution-map"><!-- small table: project → role → notable packages --></section>

    <section id="candidates" class="space-y-10"><!-- one <article> per candidate --></section>

    <section id="top-recommendation"><!-- one larger card --></section>

  </main>
</body>
</html>
```

## Report structure

1. **Header** — solution name, date, counts, legend. No introduction paragraph; go straight to content.
2. **Solution map** — the table from process step 1 (project → role → notable packages), rendered as a plain Tailwind table (`text-sm`, `border-b border-slate-200` rows). Keeps the report self-explanatory when shared.
3. **Candidates** — one `<article>` per candidate, strongest first.
4. **Top recommendation** — one larger card: candidate name, one sentence on why it's first, an anchor link to its card. Nothing else.

## Candidate card template

Each candidate is one `<article id="candidate-N">`. The diagram carries the weight; prose is sparse. If the diagram needs a paragraph to be understood, redraw the diagram.

```html
<article id="candidate-1" class="rounded-xl border border-slate-200 bg-white p-6 space-y-4 shadow-sm">
  <div class="flex items-start justify-between gap-4">
    <h2 class="text-xl font-serif font-semibold">Collapse the Order read path</h2>
    <div class="flex gap-2 shrink-0">
      <span class="rounded-full bg-emerald-100 text-emerald-800 text-xs font-medium px-3 py-1">Strong</span>
      <span class="rounded-full bg-slate-100 text-slate-600 text-xs font-medium px-3 py-1">smells 1+2+3</span>
    </div>
  </div>

  <ul class="font-mono text-sm text-slate-600 space-y-0.5">
    <li>src/Api/Endpoints/OrderEndpoints.cs</li>
    <li>src/Application/Services/OrderService.cs <span class="text-slate-400">— 14/17 methods forward</span></li>
    <li>src/Infrastructure/Repositories/OrderRepository.cs</li>
  </ul>

  <!-- Before / After — the centerpiece -->
  <div class="grid grid-cols-2 gap-4">
    <div class="rounded-lg border border-slate-200 p-4">
      <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">Before</p>
      <!-- diagram -->
    </div>
    <div class="rounded-lg border border-slate-200 p-4">
      <p class="text-xs uppercase tracking-wider text-slate-400 mb-2">After</p>
      <!-- diagram -->
    </div>
  </div>

  <p class="text-sm"><span class="font-semibold">Problem:</span> Three shallow modules and two one-adapter seams sit between the endpoint and the query.</p>
  <p class="text-sm"><span class="font-semibold">Solution:</span> Endpoint projects straight from DbContext; delete OrderService, OrderRepository, and both interfaces.</p>

  <ul class="text-sm space-y-1 list-disc list-inside text-slate-700">
    <li>locality: the query lives where it's used</li>
    <li>delete 2 modules, 2 interfaces, 31 mock setups</li>
    <li>tests hit real SQL via SQLite in-memory</li>
  </ul>

  <!-- only when a recorded decision is contradicted -->
  <p class="rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-sm px-3 py-2">
    Contradicts ADR-0007 (repository pattern) — worth reopening because the seam has had one adapter for 2 years.
  </p>
</article>
```

Required fields per card, in this order: title, badges, files (with evidence counts inline), before/after diagram, problem (one sentence), solution (one sentence), wins (≤6 words each), optional ADR callout.

## Diagram patterns

Pick per candidate; vary across the report so it doesn't look generated. Keep each diagram ≤ ~320px tall so before/after sits side by side. Module labels inside diagrams use `text-xs uppercase tracking-wider`.

### Mermaid flowchart — call chains and dependencies (the workhorse)

Use when the point is "X calls Y calls Z, and look at the mess." Color leaks red, deep modules dark:

```html
<pre class="mermaid">
flowchart TB
  EP[OrderEndpoints] --> S[IOrderService]
  S --> SI[OrderService]
  SI --> R[IOrderRepository]
  R --> RI[OrderRepository]
  RI --> DB[(DbContext)]
  RI -. IQueryable leaks .-> EP
  classDef leak stroke:#dc2626,stroke-width:2px,color:#dc2626;
  classDef deep fill:#1e293b,color:#f8fafc,stroke:#1e293b;
  class DB deep
  linkStyle 5 stroke:#dc2626,stroke-dasharray:4;
</pre>
```

The "after" version of the same flowchart is short — two or three nodes with the deep module dark. The visual contrast in node count *is* the argument.

### Mass diagram — "interface as wide as implementation" (hand-built divs)

Two bars per module: interface surface on top, implementation below. Shallow = nearly equal heights; deep = thin interface over a tall implementation.

```html
<div class="flex items-end gap-6 h-48">
  <div class="flex flex-col w-28 gap-px">
    <div class="bg-slate-400 h-20 flex items-center justify-center text-[10px] uppercase tracking-wider text-white">interface</div>
    <div class="bg-slate-700 h-24 flex items-center justify-center text-[10px] uppercase tracking-wider text-white">impl</div>
    <p class="text-xs text-center pt-1 text-slate-500">OrderService — shallow</p>
  </div>
  <div class="flex flex-col w-28 gap-px">
    <div class="bg-slate-400 h-6 flex items-center justify-center text-[10px] uppercase tracking-wider text-white">interface</div>
    <div class="bg-slate-800 h-40 flex items-center justify-center text-[10px] uppercase tracking-wider text-white">impl</div>
    <p class="text-xs text-center pt-1 text-slate-500">DbContext — deep</p>
  </div>
</div>
```

### Cross-section — layered shallowness

Stacked horizontal bands, one per layer a call passes through. Before: five thin bands (`h-8`) each labelled with the file it lives in. After: one thick band (`h-24`) labelled with the consolidated responsibility. Good for smell 1 and smell 7.

### Collapse diagram — before: nested boxes; after: one box with internals faded

Render the "before" call tree as nested bordered `<div>`s. The "after" is the outermost box with a thick dark border (`border-4 border-slate-800`) and the formerly-separate modules shown inside at `opacity-40` — they still exist as code, but they're no longer interface.

### Sequence diagram — round-trip counting

Mermaid `sequenceDiagram` when the argument is "before: 6 hops to answer one request; after: 1." Works well for MediatR ceremony (smell 5).

## Badges and colors

- `Strong` → `bg-emerald-100 text-emerald-800`
- `Worth exploring` → `bg-amber-100 text-amber-800`
- `Speculative` → `bg-slate-100 text-slate-600`
- Leaks/red: `#dc2626` only. Warnings/amber callouts: `bg-amber-50 border-amber-200 text-amber-800`. One accent color (emerald) for wins; everything else stone/slate. Restraint is the style.

## Tone and wording

Plain English, concise; architectural nouns come from the SKILL.md vocabulary table, used exactly.

**Use:** module, interface, implementation, deep, shallow, seam, adapter, locality, leverage.
**Never:** component, layer-as-praise, boundary (for seam), "cleaner", "more maintainable", "best practice".

Phrasings that fit:

- "OrderService is shallow — 14 of 17 methods forward to the repository."
- "The seam has one adapter; the second is a mock."
- "IQueryable leaks across the seam — callers compose SQL anyway."
- "Deepen: one interface, one place to test."

**Win bullets** name the gain in vocabulary terms with numbers where possible: *"locality: pricing bugs concentrate in one module"*, *"leverage: one projection, 6 call sites"*, *"delete 4 files, 31 mock setups"*. Never *"easier to maintain"* — if you can't name the win concretely, the candidate is weaker than you think.

No hedging, no "it's worth noting". If a sentence could be a bullet, make it a bullet. If a bullet could be cut, cut it.
