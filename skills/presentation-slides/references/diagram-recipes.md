# Diagram Recipes (Mermaid) — for slides

Every diagram is authored as a `.mmd` file in `<output>/diagrams/`, rendered
to `.png` by `scripts/render_diagrams.py`, and placed on slides by
`build_pptx.py`. Source and image both stay in `diagrams/` so the user can
edit and re-render later.

## Slides are not documents — keep diagrams lean

A slide diagram is read from the back of a room in ~10 seconds. Rules that
matter more here than in written docs:

1. **≤ 10 nodes per diagram.** Merge trivial class libraries into one box
   ("Domain + Application") rather than drawing every project.
2. **Prefer landscape.** Slides are 16:9 — use `flowchart LR` for context
   and deployment. `flowchart TB` is fine for the container view only when
   it has ≤ 3 layers. A tall skinny diagram renders tiny on a slide.
3. **Short labels.** Two lines max: name, then technology (`<br/>` breaks).
4. Sequence diagrams: **≤ 5 participants and ≤ 10 messages**, or it becomes
   unreadable wallpaper. Show the happy path; error handling goes in
   speaker notes.

## Hard rules — renderers fail if you break these

1. A `.mmd` file contains **only Mermaid source**. No markdown code fences,
   no headings, no prose. First line: the init directive below; second line:
   the diagram type.
2. Node IDs are plain identifiers (`api`, `orderSvc`) — letters, digits,
   underscores only. Display text goes in the label, never in the ID.
3. Any label with spaces, parentheses, slashes, dots, or `&` must be quoted:
   `api["ShopLite.Api (ASP.NET Core)"]`. Unquoted `(`, `)`, `&` are the #1
   cause of render failures.
4. `<br/>` for line breaks inside labels, never `\n`.
5. One diagram per file.

## Standard init directive — first line of every .mmd

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
```

## Standard palette

Apply these `classDef`s in flowcharts so colors match the deck theme and the
draw.io exports:

```
classDef person fill:#1F3864,stroke:#152848,color:#ffffff
classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
classDef external fill:#f5f5f5,stroke:#666666,color:#333333
classDef datastore fill:#ffe6cc,stroke:#d79b00,color:#663c00
```

---

## 01 — System context (`flowchart LR`)

Who uses the system and which external systems it talks to. Actors left,
system in a subgraph, externals right. Label every edge with what flows.

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

## 02 — Container / project view (`flowchart TB` or `LR`)

The deployable units, the key class libraries (grouped if numerous), data
stores, external services. Edge labels name the mechanism (project ref,
HTTPS, EF Core).

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart TB
    subgraph solution["ShopLite Solution"]
        api["ShopLite.Api<br/>Web API - net10.0"]
        core["Domain + Application<br/>Business logic"]
        infra["ShopLite.Infrastructure<br/>EF Core, Stripe client"]
    end
    db[("SQL Server")]
    stripe["Stripe API"]

    api -->|"project ref"| core
    infra -->|"project ref"| core
    infra -->|"EF Core"| db
    infra -->|"HTTPS"| stripe

    classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
    classDef external fill:#f5f5f5,stroke:#666666,color:#333333
    classDef datastore fill:#ffe6cc,stroke:#d79b00,color:#663c00
    class api system
    class core,infra internal
    class stripe external
    class db datastore
```

## 03 — Key runtime flow (`sequenceDiagram`)

The one flow that best explains the system at runtime (main business
transaction, background job, auth handshake). Participants are real classes
from the code.

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

Pitfalls: aliases (`participant API as OrdersController`) keep lifelines
narrow; `->>` call, `-->>` return; no `;` inside message text.

## 04 — Data model (`erDiagram`)

Entities from the `DbContext`. **≤ 6 entities** on a slide — pick the core
aggregate, not every table. Attribute rows are `type name` with single-word
types (`int`, `string`, `datetime`, `decimal` — `decimal(18,2)` breaks the
parser). 3–5 telling attributes per entity, not every column.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_LINE : contains
    PRODUCT ||--o{ ORDER_LINE : "appears in"
    CUSTOMER {
        int Id PK
        string Email
    }
    ORDER {
        int Id PK
        int CustomerId FK
        datetime PlacedAt
        decimal Total
    }
```

Cardinality: `||` exactly one, `o|` zero or one, `}|` one or more, `}o` zero
or more.

## 05 — Deployment view (`flowchart LR`)

Where the containers run, based on evidence: Dockerfile, docker-compose, K8s
manifests, CI/CD pipelines, connection strings. Subgraphs for hosts/clusters/
cloud services. No deployment evidence in the repo → draw the local
development topology and say so on the slide's caption or notes.

---

## Render loop

After writing all `.mmd` files:

```
python "<skill>/scripts/render_diagrams.py" "<output>/diagrams"
```

If a diagram FAILs, the script prints the renderer's error naming the bad
line. Fix that `.mmd` and re-run — it re-renders everything, which is cheap.
Do not build the deck until every diagram renders OK: `build_pptx.py` will
fail on the missing PNGs anyway.
