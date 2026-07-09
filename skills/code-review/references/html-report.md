# HTML Report Format

The review is one self-contained HTML file written to the OS temp directory. Tailwind (styling) loads from a CDN; there is no other JavaScript. Follow this document closely — copy the scaffold and the card template, then fill in content. Do not invent a different layout.

## Contents

1. [File mechanics](#file-mechanics)
2. [Escaping rules — read first](#escaping-rules--read-first)
3. [Scaffold](#scaffold)
4. [Report structure](#report-structure)
5. [Finding card template](#finding-card-template)
6. [Code snippet styling](#code-snippet-styling)
7. [Badges and colors](#badges-and-colors)
8. [Verdict section](#verdict-section)
9. [Tone and wording](#tone-and-wording)

## File mechanics

- Path: `<tempdir>/code-review-<yyyyMMdd-HHmmss>.html`. Temp dir: `$env:TEMP` on Windows, `$TMPDIR` falling back to `/tmp` on macOS/Linux. Never write into the repository.
- Open after writing: `Start-Process <path>` (Windows PowerShell), `open <path>` (macOS), `xdg-open <path>` (Linux).
- Always tell the user the absolute path in chat — auto-open can fail, and the Tailwind CDN needs a network connection.

## Escaping rules — read first

Every code snippet in the report is C# pasted inside HTML. Before pasting, replace in this order:

1. `&` → `&amp;`
2. `<` → `&lt;`
3. `>` → `&gt;`

Generics make this non-negotiable: an unescaped `List<Order>` becomes an HTML tag, silently swallows the rest of the snippet, and the report *looks* fine at a glance while showing wrong code. `&&` becomes `&amp;&amp;`, `x => x.Id` becomes `x =&gt; x.Id`. Check every snippet, not just the ones that look risky.

## Scaffold

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Code review — {{scope, e.g. "feature/checkout vs main"}}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-50 text-slate-900 font-sans">
  <main class="max-w-4xl mx-auto px-6 py-12 space-y-10">

    <header class="space-y-3">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h1 class="text-3xl font-serif font-semibold">Code review — {{solution/repo name}}</h1>
          <p class="text-sm text-slate-500 mt-1">{{scope description}} · {{date}} · {{N}} files, +{{added}} −{{removed}}</p>
        </div>
        <!-- verdict badge: see Verdict section for the three variants -->
        <span class="rounded-full bg-red-100 text-red-800 text-sm font-semibold px-4 py-1.5 shrink-0">Request changes</span>
      </div>

      <!-- stat tiles -->
      <div class="grid grid-cols-4 gap-3 pt-2">
        <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p class="text-2xl font-semibold text-red-700">{{n}}</p>
          <p class="text-xs uppercase tracking-wider text-red-600">Blockers</p>
        </div>
        <div class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <p class="text-2xl font-semibold text-amber-700">{{n}}</p>
          <p class="text-xs uppercase tracking-wider text-amber-600">Warnings</p>
        </div>
        <div class="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3">
          <p class="text-2xl font-semibold text-sky-700">{{n}}</p>
          <p class="text-xs uppercase tracking-wider text-sky-600">Suggestions</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p class="text-2xl font-semibold text-slate-700">{{n}}</p>
          <p class="text-xs uppercase tracking-wider text-slate-500">Files reviewed</p>
        </div>
      </div>
    </header>

    <section id="files"><!-- files table --></section>

    <section id="findings" class="space-y-8"><!-- one <article> per finding, Blockers first --></section>

    <section id="verdict"><!-- verdict card --></section>

  </main>
</body>
</html>
```

## Report structure

1. **Header** — scope, date, diff stat, verdict badge, stat tiles. No introduction paragraph; go straight to content.
2. **Files table** — one row per reviewed file: path (monospace), `+/−` line counts, finding count with severity dots. Plain Tailwind table, `text-sm`, `border-b border-slate-200` rows. A file with zero findings still gets a row — it shows the review covered it.
3. **Findings** — one `<article>` per finding: all Blockers, then Warnings, then Suggestions. Number them `#1, #2…` in that order; the chat summary and verdict list refer to these numbers.
4. **Verdict** — one card: the verdict, one sentence of justification, and the fix-first list.

If there are zero findings, replace the findings section with a single quiet card — `border-emerald-200 bg-emerald-50`, one sentence: "No defects found in {{N}} files. Checked: async usage, EF Core queries, auth coverage, input validation, lifetimes." Naming what was checked is what makes an empty report credible.

## Finding card template

```html
<article id="finding-1" class="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
  <!-- header strip: severity-tinted -->
  <div class="flex items-start justify-between gap-4 px-6 py-4 bg-red-50 border-b border-red-100">
    <h2 class="text-lg font-serif font-semibold">#1 — Interpolated user input in FromSqlRaw</h2>
    <div class="flex gap-2 shrink-0">
      <span class="rounded-full bg-red-100 text-red-800 text-xs font-semibold px-3 py-1">Blocker</span>
      <span class="rounded-full bg-slate-100 text-slate-600 text-xs font-medium px-3 py-1">Security</span>
    </div>
  </div>

  <div class="p-6 space-y-4">
    <p class="font-mono text-sm text-slate-600">src/Api/Endpoints/SearchEndpoints.cs:42</p>

    <!-- offending code -->
    <div>
      <p class="text-xs uppercase tracking-wider text-slate-400 mb-1.5">Found</p>
      <pre class="rounded-lg bg-slate-900 text-slate-100 text-sm leading-relaxed p-4 overflow-x-auto"><code>var term = req.Query["q"];
<span class="block bg-red-500/25 -mx-4 px-4">var rows = await db.Products
    .FromSqlRaw($"SELECT * FROM Products WHERE Name LIKE '%{term}%'")</span>
    .ToListAsync(ct);</code></pre>
    </div>

    <!-- fixed code -->
    <div>
      <p class="text-xs uppercase tracking-wider text-slate-400 mb-1.5">Fix</p>
      <pre class="rounded-lg bg-slate-900 text-slate-100 text-sm leading-relaxed p-4 overflow-x-auto border-l-4 border-emerald-500"><code>var rows = await db.Products
    .FromSql($"SELECT * FROM Products WHERE Name LIKE {"%" + term + "%"}")
    .ToListAsync(ct);</code></pre>
    </div>

    <p class="text-sm"><span class="font-semibold">Why:</span> FromSqlRaw treats the interpolated string as SQL text — <code class="text-xs bg-slate-100 rounded px-1">q='; DROP TABLE Products;--</code> executes. FromSql parameterizes each interpolation hole.</p>
  </div>
</article>
```

Required fields per card, in this order: numbered title, severity badge, category chip, `file:line` (monospace), Found snippet with the offending line(s) highlighted, Fix snippet, Why (one or two sentences naming the concrete failure scenario). Optional additions:

- A second `file:line` when the finding spans two sites (e.g. a changed method + its broken caller) — list both, snippet the more damning one.
- A `pre-existing` chip (`bg-slate-100 text-slate-500`) when the defect predates the diff but is reported under the SKILL.md scope rules.

Header-strip tint follows severity: Blocker `bg-red-50 border-red-100`, Warning `bg-amber-50 border-amber-100`, Suggestion `bg-sky-50 border-sky-100`.

## Code snippet styling

- Dark block: `bg-slate-900 text-slate-100 text-sm leading-relaxed p-4 rounded-lg overflow-x-auto`.
- Highlight the offending line(s) with `<span class="block bg-red-500/25 -mx-4 px-4">…</span>` inside the `<code>` — the negative margin makes the highlight run edge to edge.
- The Fix block gets `border-l-4 border-emerald-500` instead of any highlight.
- No syntax-highlighting library. Plain text in a dark block reads fine and can't break.
- Keep snippets to the offending line ± 2–4 context lines. If a snippet needs more than ~12 lines to make sense, quote less and let the Why carry it.
- Preserve the original indentation, then re-check the escaping rules.

## Badges and colors

- Severity: `Blocker` → `bg-red-100 text-red-800` · `Warning` → `bg-amber-100 text-amber-800` · `Suggestion` → `bg-sky-100 text-sky-800`
- Category chips (always `bg-slate-100 text-slate-600`): `Async`, `Data access`, `Security`, `Correctness`, `Lifetimes`, `API contract`, `Performance`, `Tests`
- Severity dots in the files table: `<span class="inline-block w-2 h-2 rounded-full bg-red-500"></span>` (red/amber/sky, one dot per finding).
- Emerald appears only in Fix borders, the Approve verdict, and the zero-findings card. Everything else stone/slate. Restraint is the style.

## Verdict section

The badge text and colors come straight from the SKILL.md rule:

| Verdict | When | Badge classes |
|---------|------|---------------|
| Request changes | ≥1 Blocker | `bg-red-100 text-red-800` |
| Approve with reservations | 0 Blockers, ≥1 Warning | `bg-amber-100 text-amber-800` |
| Approve | 0 Blockers, 0 Warnings | `bg-emerald-100 text-emerald-800` |

```html
<section id="verdict" class="rounded-xl border-2 border-red-200 bg-white p-6 space-y-3">
  <div class="flex items-center gap-3">
    <span class="rounded-full bg-red-100 text-red-800 text-sm font-semibold px-4 py-1.5">Request changes</span>
    <p class="text-sm text-slate-600">2 Blockers must be fixed before merge.</p>
  </div>
  <ol class="text-sm list-decimal list-inside space-y-1 text-slate-700">
    <li><a href="#finding-1" class="underline decoration-slate-300 hover:decoration-slate-600">#1 SQL injection in SearchEndpoints</a> — fix first, it's exploitable today</li>
    <li><a href="#finding-2" class="underline decoration-slate-300 hover:decoration-slate-600">#2 Missing [Authorize] on AdminEndpoints</a></li>
    <li><a href="#finding-3" class="underline decoration-slate-300 hover:decoration-slate-600">#3 N+1 in order listing</a> — before the next data-heavy demo</li>
  </ol>
</section>
```

The fix-first list is ordered by *what to do first*, which usually but not always matches severity order — say why when it doesn't. Border color of the card follows the verdict (red/amber/emerald `-200`).

## Tone and wording

Write like a senior engineer leaving review comments, not like a scanner producing output.

- Title = the defect, named plainly: "Interpolated user input in FromSqlRaw", not "Potential SQL Injection Vulnerability Detected".
- Why = the failure scenario with concrete input/state: "any authenticated user can fetch other users' invoices by iterating ids", not "this may pose a security risk".
- No hedging ("might possibly"), no filler ("it's worth noting"), no severity inflation in prose — the badge already says it.
- Numbers beat adjectives: "201 queries for a 200-order page", not "many unnecessary queries".
- The Fix snippet must compile in context — same variable names as the Found snippet, real APIs only. A fix the author can't paste in erodes trust in every other card.
