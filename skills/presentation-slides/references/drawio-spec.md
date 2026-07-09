# draw.io Export Spec

`scripts/make_drawio.py` turns a small JSON spec into a fully editable
`.drawio` file (opens in [app.diagrams.net](https://app.diagrams.net) or the
draw.io desktop app / VS Code extension). You describe *what* the diagram
contains; the script computes a clean layered layout, consistent colors, and
orthogonal edges. Never hand-write draw.io XML — the spec is the interface.

Produce specs for the two structural diagrams users most often want to edit:

- `01-system-context.drawio.json` — mirror of the Mermaid system context
- `02-container.drawio.json` — mirror of the Mermaid container view

Keep each spec consistent with its Mermaid twin: same nodes, same edges, same
labels. The Mermaid version (rendered to .png) is what appears on the slides;
the draw.io version is the user's editable copy.

## Spec format

```json
{
  "name": "02-container",
  "title": "ShopLite — Container Diagram",
  "layers": [
    { "label": "Clients",
      "nodes": [
        {"id": "spa", "label": "Web Browser\nReact SPA", "type": "external"}
      ] },
    { "label": "ShopLite System",
      "nodes": [
        {"id": "api",    "label": "ShopLite.Api\nASP.NET Core Web API", "type": "primary"},
        {"id": "worker", "label": "ShopLite.Worker\nBackground Service", "type": "primary"}
      ] },
    { "label": "Data & External Services",
      "nodes": [
        {"id": "db",     "label": "SQL Server\nshoplite-db", "type": "datastore"},
        {"id": "stripe", "label": "Stripe\nPayments API",    "type": "external"}
      ] }
  ],
  "edges": [
    {"from": "spa",    "to": "api", "label": "HTTPS / JSON"},
    {"from": "api",    "to": "db",  "label": "EF Core"},
    {"from": "api",    "to": "stripe", "label": "REST"},
    {"from": "worker", "to": "db",  "label": "EF Core"}
  ]
}
```

Rules:

- `layers` are drawn top to bottom as labelled dashed bands; order them by
  distance from the user (clients → apps → data/external).
- Node `id`s must be unique across all layers; every edge endpoint must be a
  declared `id`. The script validates this and fails with a clear message.
- `\n` inside a label makes a line break (name on line 1, technology on line 2).
- Aim for 2–4 layers and at most ~5 nodes per layer.

## Node types

| type        | Rendering                       | Use for                                  |
|-------------|---------------------------------|------------------------------------------|
| `primary`   | blue rounded box                | this solution's projects / executables   |
| `secondary` | green rounded box               | supporting internal libraries/components |
| `accent`    | yellow rounded box              | queues, caches, background jobs          |
| `external`  | grey box                        | users' clients, third-party systems      |
| `datastore` | orange cylinder                 | databases, blob storage                  |

## Command

```
python "<skill>/scripts/make_drawio.py" "<output>/diagrams/01-system-context.drawio.json" "<output>/diagrams/02-container.drawio.json"
```

This writes `01-system-context.drawio` and `02-container.drawio` next to the
specs. Leave the `.drawio.json` files in place — they are the regeneration
source if the user wants layout tweaks re-applied.
