# Diagram Recipes (Mermaid)

Every diagram is authored as a `.mmd` file in the `diagrams/` output folder, then
rendered to `.png` by `scripts/render_diagrams.py`. Both files stay in `diagrams/`
so the user can edit the source and re-render later.

## Hard rules — renderers fail if you break these

1. A `.mmd` file contains **only Mermaid source**. No markdown code fences
   (```` ``` ````), no headings, no prose. The first non-comment line must be the
   init directive below, and the second the diagram type (`flowchart LR`, etc.).
2. Node IDs are plain identifiers (`api`, `orderSvc`) — letters, digits,
   underscores only. Put display text in the label, never in the ID.
3. Any label containing spaces, parentheses, slashes, dots, or `&` must be
   quoted: `api["ShopLite.Api (ASP.NET Core)"]`. Unquoted `(`, `)` and `&`
   are the #1 cause of render failures.
4. Use `<br/>` for line breaks inside labels, not `\n`.
5. Keep each diagram to **15 nodes or fewer**. If a component diagram grows past
   that, split it or drop the trivial members — a readable diagram beats a
   complete one.
6. One diagram per file.

## Standard init directive

Start every `.mmd` file with this line — it gives all diagrams a consistent,
print-friendly look in both local and kroki renderers:

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
```

## Standard palette

Apply these `classDef`s in flowcharts so colors match the draw.io exports:

```
classDef person fill:#1F3864,stroke:#152848,color:#ffffff
classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
classDef internal fill:#d5e8d4,stroke:#82b366,color:#1f3864
classDef external fill:#f5f5f5,stroke:#666666,color:#333333
classDef datastore fill:#ffe6cc,stroke:#d79b00,color:#663c00
```

---

## 01 — System context (`flowchart LR`)

Who uses the system, and which external systems it talks to. Actors on the
left, the system in a subgraph, externals on the right. Every edge labelled
with what flows and how.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart LR
    customer(["Customer"])
    admin(["Store Admin"])
    subgraph shoplite["ShopLite System"]
        api["ShopLite.Api<br/>ASP.NET Core Web API"]
    end
    stripe["Stripe<br/>Payment Gateway"]
    smtp["SMTP Server"]

    customer -->|"Browses, orders (HTTPS)"| api
    admin -->|"Manages catalog (HTTPS)"| api
    api -->|"Charges cards (REST)"| stripe
    api -->|"Sends receipts (SMTP)"| smtp

    classDef person fill:#1F3864,stroke:#152848,color:#ffffff
    classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    classDef external fill:#f5f5f5,stroke:#666666,color:#333333
    class customer,admin person
    class api system
    class stripe,smtp external
```

## 02 — Container / project view (`flowchart TB`)

The deployable units (each executable project), the class-library projects
they reference, and the data stores. Edge labels name the mechanism
(project reference, HTTPS, EF Core, connection string).

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart TB
    subgraph solution["ShopLite Solution"]
        api["ShopLite.Api<br/>Web API - net10.0"]
        app["ShopLite.Application<br/>Use cases"]
        domain["ShopLite.Domain<br/>Entities and rules"]
        infra["ShopLite.Infrastructure<br/>EF Core, Stripe client"]
    end
    db[("SQL Server")]
    stripe["Stripe API"]

    api -->|"project ref"| app
    app -->|"project ref"| domain
    infra -->|"project ref"| app
    infra -->|"EF Core"| db
    infra -->|"HTTPS"| stripe

    classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
    classDef external fill:#f5f5f5,stroke:#666666,color:#333333
    classDef datastore fill:#ffe6cc,stroke:#d79b00,color:#663c00
    class api system
    class app,domain,infra internal
    class stripe external
    class db datastore
```

## 03 — Component view of the core project (`flowchart TB`)

Zoom into the project where the behavior lives: endpoint groups/controllers,
handlers/services, domain entry points, outbound adapters. Group with
subgraphs by folder or responsibility. Only include components you actually
found in the code — name real classes.

## 04 — Key runtime flow (`sequenceDiagram`)

Pick the 1–2 flows that best explain how the system works at runtime (the
main business transaction, a background job, an auth handshake). Participants
are the real classes/containers from diagram 02/03.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
sequenceDiagram
    autonumber
    actor Customer
    participant API as OrdersController
    participant Svc as OrderService
    participant DB as ShopContext (SQL Server)
    participant Pay as StripeClient

    Customer->>API: POST /api/orders
    API->>Svc: PlaceOrderAsync(dto)
    Svc->>DB: Load cart, validate stock
    Svc->>Pay: CreateCharge(amount)
    Pay-->>Svc: chargeId
    Svc->>DB: SaveChanges (order + payment)
    API-->>Customer: 201 Created
```

Sequence pitfalls: participant aliases (`participant API as OrdersController`)
keep lifelines narrow; `->>` solid call, `-->>` return; no quotes needed in
message text, but avoid `;` inside messages.

## 05 — Data model (`erDiagram`)

Entities from the `DbContext` and their relationships. Attribute rows are
`type name` with **single-word types** (`int`, `string`, `datetime`, `decimal`) —
`decimal(18,2)` breaks the parser. List only key attributes (PK, FKs, 3–6
telling fields), not every column.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_LINE : contains
    PRODUCT ||--o{ ORDER_LINE : "appears in"
    CUSTOMER {
        int Id PK
        string Email
        string Name
    }
    ORDER {
        int Id PK
        int CustomerId FK
        datetime PlacedAt
        decimal Total
        string Status
    }
```

Relationship cardinality: `||` exactly one, `o|` zero or one, `}|` one or
more, `}o` zero or more.

## 06 — Deployment view (`flowchart TB`)

Where the containers run. Base it on evidence: Dockerfile, docker-compose,
Kubernetes manifests, CI/CD pipelines, appsettings connection strings. Use
subgraphs for hosts/clusters/cloud services. If there is no deployment
evidence in the repo, draw a typical development setup and say so in the
document ("no deployment configuration found in the repository; the diagram
shows the local development topology").

---

## Render loop

After writing all `.mmd` files:

```
python "<skill>/scripts/render_diagrams.py" "<output>/diagrams"
```

If a diagram FAILs, the script prints the renderer's error, which names the
bad line. Fix that `.mmd` file and re-run — the script re-renders everything,
which is cheap. Do not proceed to the document build until every diagram
renders OK.
