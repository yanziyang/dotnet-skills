# draw.io ERD Export Spec

`scripts/make_drawio_erd.py` turns a JSON spec into a fully editable
`.drawio` ER diagram (opens in [app.diagrams.net](https://app.diagrams.net),
the draw.io desktop app, or the VS Code extension). Entities are native
draw.io table shapes — the user can add columns, drag entities, and re-route
relationships. Never hand-write draw.io XML; the spec is the interface.

Produce one spec per ERD the document shows:

- `01-erd-<module>.drawio.json` — one per module ERD (or `01-erd-full` when
  the database is small enough for a single diagram)

Keep each spec consistent with its Mermaid twin: same entities, same
relationships, same key markers. The Mermaid version (rendered to .png) is
what appears in the document; the draw.io version is the user's editable
copy. Include stub entities (see erd-recipes.md) as entities with only their
PK column.

## Spec format

```json
{
  "name": "01-erd-ordering",
  "title": "Ordering Module - Entity Relationship Diagram",
  "entities": [
    { "id": "order", "name": "Order",
      "columns": [
        {"name": "Id",         "type": "int",           "key": "PK"},
        {"name": "CustomerId", "type": "int",           "key": "FK"},
        {"name": "PlacedAt",   "type": "datetime2"},
        {"name": "Notes",      "type": "nvarchar(500)", "nullable": true}
      ] },
    { "id": "customer", "name": "Customer",
      "columns": [ {"name": "Id", "type": "int", "key": "PK"} ] }
  ],
  "relations": [
    {"from": "customer", "to": "order", "label": "places", "cardinality": "1:N"}
  ]
}
```

Rules:

- Entity `id`s must be unique; every relation endpoint must be a declared
  `id`. The script validates this and fails with a clear message.
- Column `key` is `"PK"`, `"FK"`, or omitted; key rows render bold.
- `"nullable": true` appends a `(null)` marker; omitted means NOT NULL.
- Full column types (with lengths/precision) are fine here — unlike Mermaid,
  draw.io has no type parser to break. Match the DDL exactly.
- `cardinality` is `"from-side:to-side"`, each side one of `1`, `0..1`, `N`,
  `0..N` — rendered as crow's-foot line ends. `"1:N"` = one parent, many
  children.
- Entities are laid out in a grid, three per row, in spec order. Put related
  entities next to each other; the user can rearrange freely afterwards.
- Match the Mermaid twin's attribute selection (PK, FKs, 3–6 telling
  columns) rather than dumping all columns — a 40-row entity box is not an
  editable diagram, it is a wall.

## Command

```
python "<skill>/scripts/make_drawio_erd.py" "<output>/diagrams/01-erd-ordering.drawio.json" "<output>/diagrams/02-erd-catalog.drawio.json"
```

This writes `01-erd-ordering.drawio` etc. next to the specs. Leave the
`.drawio.json` files in place — they are the regeneration source.
