# deck.json Spec — input for `scripts/build_pptx.py`

The deck is described as content-only JSON; the build script owns all layout,
colors, and fonts (16:9, Segoe UI, navy #1F3864 + blue #2E75B6 — the same
palette as the diagrams). Never generate .pptx with hand-written python-pptx
code — write a `deck.json` and run the script. That is what keeps every deck
consistent and editable.

```
python "<skill>/scripts/build_pptx.py" "<output>/deck.json" "<output>/<Name>-Overview.pptx"
```

Image paths are resolved **relative to deck.json**, so with deck.json in
`<output>/` a diagram is referenced as `diagrams/01-system-context.png`.
The script validates everything and exits non-zero with one line per problem
(unknown type, missing image, ragged table row). Fix the spec and re-run.

## Top level

```json
{
  "title": "ShopLite",
  "footer": "ShopLite - Solution Overview",
  "slides": [ ... ]
}
```

`footer` is optional; it appears bottom-left on light slides, with the slide
number bottom-right. Dark slides (title, section, closing) have no footer.

## Slide types

Every slide object has a `"type"`, usually a `"title"`, and an optional
`"notes"` (speaker notes — write them; presenters rely on them, and they are
the natural place for detail that must not clutter the slide).

### `title` — cover slide (dark)
```json
{ "type": "title", "title": "ShopLite", "subtitle": "Solution Overview",
  "author": "Platform Team", "date": "July 2026",
  "meta": "Confidential", "notes": "..." }
```
`author`, `date`, `meta` are each optional; they join into one meta line.

### `section` — divider (dark)
```json
{ "type": "section", "number": 2, "title": "How It's Built",
  "subtitle": "Architecture and technology choices" }
```

### `bullets` — title + bulleted list
```json
{ "type": "bullets", "title": "What Is ShopLite?",
  "subtitle": "optional small caption next to the title rule",
  "bullets": [
    "**Online storefront** for small retailers - catalog, cart, checkout",
    { "text": "Built on ASP.NET Core (net10.0)", "level": 1 }
  ] }
```
Items are strings or `{"text", "level"}` (level 0 or 1). `**bold**` works in
any text field on any slide type. Keep it to **at most 6 level-0 bullets,
~12 words each** — the script shrinks the font when text is long, but a
wall of words is a bad slide no matter the font size. Move detail to `notes`.

### `two_column` — comparison / paired lists
```json
{ "type": "two_column", "title": "Today vs. Target",
  "columns": [
    { "heading": "Today",  "bullets": ["Monolith deployment", "..."] },
    { "heading": "Target", "bullets": ["Split worker service", "..."] }
  ] }
```

### `cards` — 2–6 titled boxes in a grid (tech stack, capabilities, roles)
```json
{ "type": "cards", "title": "Technology Stack",
  "cards": [
    { "title": "ASP.NET Core 10", "text": "REST API, minimal APIs, JWT auth" },
    { "title": "EF Core + SQL Server", "text": "Code-first, 12 migrations" }
  ] }
```
Card text must stay short (≤ 2 sentences). 3 or 6 cards → rows of three;
2 or 4 → rows of two.

### `stats` — 2–5 big numbers, optional bullets underneath
```json
{ "type": "stats", "title": "The Solution at a Glance",
  "stats": [
    { "value": "7", "label": "projects in the solution" },
    { "value": "42", "label": "API endpoints" },
    { "value": "net10.0", "label": "target framework" }
  ],
  "bullets": ["optional follow-up points below the numbers"] }
```
Only use numbers you actually counted in the repo.

### `image` — full-width diagram with caption
```json
{ "type": "image", "title": "System Context",
  "image": "diagrams/01-system-context.png",
  "caption": "Editable sources: diagrams/01-system-context.mmd / .drawio" }
```
The picture is auto-fitted and centered, aspect ratio preserved.

### `image_bullets` — diagram beside talking points
```json
{ "type": "image_bullets", "title": "Placing an Order",
  "image": "diagrams/03-sequence-place-order.png", "image_side": "right",
  "bullets": ["Stock is validated before payment", "..."] }
```
`image_side`: `"left"` or `"right"` (default). Use ≤ 4 short bullets — the
text column is narrow.

### `table` — small comparison or inventory table
```json
{ "type": "table", "title": "Projects",
  "columns": ["Project", "Kind", "Purpose"],
  "rows": [["ShopLite.Api", "Web API", "HTTP surface"],
           ["ShopLite.Domain", "Class library", "Entities and rules"]] }
```
Max ~5 columns and ~8 rows; every row must match the column count. Larger
inventories belong in a document, not a slide — show the top rows and say so.

### `timeline` — 3–6 step roadmap / process (horizontal chevrons)
```json
{ "type": "timeline", "title": "Roadmap",
  "steps": [
    { "label": "Q3 2026", "text": "Split background worker" },
    { "label": "Q4 2026", "text": "Multi-tenant support" }
  ] }
```
`label` is the short text inside the chevron; `text` appears below it.

### `closing` — thank-you / next steps (dark)
```json
{ "type": "closing", "title": "Thank You",
  "subtitle": "Questions?",
  "lines": ["Repo: github.com/acme/shoplite", "Contact: platform-team@acme.com"] }
```

## Quality rules

- A slide makes **one point**; its title should state that point where
  possible ("EF Core owns all data access", not just "Data layer").
- Prefer a diagram (`image`) or structure (`cards`, `stats`, `table`,
  `timeline`) over yet another bullet list — decks that alternate slide
  types read as far more professional.
- Numbers and names must come from the repo scan; never invent metrics.
- Speaker notes on every content slide: 2–4 sentences of what the presenter
  should actually say, including evidence (file/class names) that backs the
  slide.
