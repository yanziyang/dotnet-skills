# draw.io Export Spec

`scripts/make_drawio.py` turns a small JSON spec into a fully editable
`.drawio` file (opens in [app.diagrams.net](https://app.diagrams.net), the
draw.io desktop app, or the VS Code extension). You describe *what* the
diagram contains; the script computes a clean layered layout, consistent
colors, and orthogonal edges. Never hand-write draw.io XML — the spec is the
interface.

Produce specs for the two structural diagrams users most often want to edit:

- `01-context.drawio.json` — mirror of the Mermaid context diagram (FS)
- `05-module-structure.drawio.json` — mirror of the Mermaid module
  structure (MDS)

Keep each spec consistent with its Mermaid twin: same nodes, same edges,
same labels. The Mermaid version is what appears in the documents; the
draw.io version is the user's editable copy.

## Spec format

```json
{
  "name": "05-module-structure",
  "title": "ShopLite — Module Structure",
  "layers": [
    { "label": "Presentation",
      "nodes": [
        {"id": "api", "label": "ShopLite.Api\nASP.NET Core Web API", "type": "primary"}
      ] },
    { "label": "Application & Domain",
      "nodes": [
        {"id": "app",    "label": "ShopLite.Application\nUse cases",      "type": "secondary"},
        {"id": "domain", "label": "ShopLite.Domain\nEntities and rules",  "type": "secondary"}
      ] },
    { "label": "Infrastructure & Data",
      "nodes": [
        {"id": "infra", "label": "ShopLite.Infrastructure\nEF Core, Stripe", "type": "secondary"},
        {"id": "db",    "label": "SQL Server",                               "type": "datastore"}
      ] }
  ],
  "edges": [
    {"from": "api",   "to": "app",    "label": "project ref"},
    {"from": "app",   "to": "domain", "label": "project ref"},
    {"from": "infra", "to": "app",    "label": "project ref"},
    {"from": "infra", "to": "db",     "label": "EF Core"}
  ]
}
```

Rules:

- `layers` are drawn top to bottom as labelled dashed bands; order them by
  distance from the user (actors/clients → application → data/external).
- Node `id`s must be unique across all layers; every edge endpoint must be a
  declared `id`. The script validates this and fails with a clear message.
- `\n` inside a label makes a line break (name on line 1, technology or role
  on line 2).
- Aim for 2–4 layers and at most ~5 nodes per layer.

## Node types

| type        | Rendering          | Use for                                  |
|-------------|--------------------|-------------------------------------------|
| `primary`   | blue rounded box   | this solution's executables / entry points |
| `secondary` | green rounded box  | internal library projects / modules        |
| `accent`    | yellow rounded box | queues, caches, background jobs            |
| `external`  | grey box           | actors' clients, third-party systems       |
| `datastore` | orange cylinder    | databases, blob storage                    |

## Command

```
python "<skill>/scripts/make_drawio.py" "<output>/diagrams/01-context.drawio.json" "<output>/diagrams/05-module-structure.drawio.json"
```

This writes `01-context.drawio` and `05-module-structure.drawio` next to the
specs. Leave the `.drawio.json` files in place — they are the regeneration
source if the user wants layout tweaks re-applied.
