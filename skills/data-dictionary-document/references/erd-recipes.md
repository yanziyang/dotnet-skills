# ERD Recipes (Mermaid) — with module breakdown rules

Every diagram is authored as a `.mmd` file in `<output>/diagrams/`, rendered
to `.png` by `scripts/render_diagrams.py`. Source and image both stay in
`diagrams/` so the user can edit and re-render later.

## When to split the ERD by module

One ERD with every table is only readable up to about **12 entities**. Count
the tables in the DDL first, then:

- **≤ 12 tables** → one full ERD: `01-erd-full.mmd`. Done.
- **> 12 tables** → split into module ERDs of **5–12 entities each**, plus a
  module overview diagram (below). Number them `01-erd-<module>.mmd`,
  `02-erd-<module>.mmd`, … in the order the document presents the modules.

### How to choose modules

Use the strongest grouping signal available, in this order:

1. **Database schemas** — if the DDL uses schemas beyond `dbo`
   (`sales.Order`, `hr.Employee`), each schema is a module.
2. **Foreign-key clusters** — tables that reference each other tightly form
   a module; the FK graph usually has visible clusters around aggregate
   roots (Order + OrderLine + Shipment; Customer + Address + Contact).
3. **Code structure** — EF Core `DbContext` boundaries, entity folder/
   namespace grouping, or feature folders in the .NET solution.
4. **Naming prefixes** — `Inv_*`, `Bill_*` style prefixes.

Name modules in business language ("Ordering", "Catalog", "Identity"), not
"Module 1". Every table belongs to exactly one module — list the mapping in
the document so nothing silently disappears.

### Cross-module relationships

When a table references a table in another module, include the referenced
entity in the module ERD **as a name-only stub** (no attribute block) so the
relationship stays visible without dragging in a whole second module. Mention
in the figure caption that stubs are defined in their own module's section.

## Module overview diagram (only when split)

`00-erd-overview.mmd` — a `flowchart LR` with one node per module showing its
table count, and one labelled edge per cross-module FK group. This is the map
the reader uses to find the right module ERD.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart LR
    identity["Identity<br/>4 tables"]
    catalog["Catalog<br/>6 tables"]
    ordering["Ordering<br/>9 tables"]
    billing["Billing<br/>5 tables"]

    ordering -->|"Order.CustomerId"| identity
    ordering -->|"OrderLine.ProductId"| catalog
    billing -->|"Invoice.OrderId"| ordering

    classDef module fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    class identity,catalog,ordering,billing module
```

## Hard rules — renderers fail if you break these

1. A `.mmd` file contains **only Mermaid source** — no code fences, headings,
   or prose. First line: the init directive; second line: `erDiagram` (or
   `flowchart LR` for the overview).
2. Entity names in `erDiagram` are single identifiers — letters, digits,
   underscores. Use the table name (`ORDER_LINE` or `OrderLine`); put
   schema prefixes in the document text, not the diagram.
3. Attribute rows are `type name` with **single-word types**: write
   `nvarchar` not `nvarchar(200)`, `decimal` not `decimal(18,2)` —
   parentheses in the type break the parser. Exact types belong in the
   document's column tables, which is where readers look them up anyway.
4. Attribute names must not contain spaces or punctuation.
5. Mark keys with `PK`, `FK`, `UK` after the name. A quoted string after
   that is an inline comment — use sparingly.
6. One diagram per file.

## Standard init directive — first line of every .mmd

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
```

## Module ERD example

Show PKs, FKs, and 3–6 telling attributes per entity — the full column list
lives in the document tables. `CUSTOMER` here is a stub from the Identity
module.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_LINE : contains
    PRODUCT ||--o{ ORDER_LINE : "appears in"
    ORDER ||--o| SHIPMENT : "ships as"

    ORDER {
        int Id PK
        int CustomerId FK
        datetime2 PlacedAt
        decimal Total
        nvarchar Status
    }
    ORDER_LINE {
        int Id PK
        int OrderId FK
        int ProductId FK
        int Quantity
        decimal UnitPrice
    }
    SHIPMENT {
        int Id PK
        int OrderId FK
        datetime2 ShippedAt
    }
```

Relationship cardinality (crow's foot, left||right of the connector):
`||` exactly one, `o|` zero or one, `}|` one or more, `}o` zero or more.
So `CUSTOMER ||--o{ ORDER` reads "one customer places zero-or-more orders".
Derive cardinality from the DDL: FK column NOT NULL → parent side `||`
(mandatory); FK nullable → `o|`; unique constraint on the FK → one-to-one.

## Render loop

After writing all `.mmd` files:

```
python "<skill>/scripts/render_diagrams.py" "<output>/diagrams"
```

If a diagram FAILs, the script prints the renderer's error naming the bad
line. Fix that `.mmd` and re-run — it re-renders everything, which is cheap.
Do not build the document until every diagram renders OK: `build_docx.py`
will flag the missing images anyway.
