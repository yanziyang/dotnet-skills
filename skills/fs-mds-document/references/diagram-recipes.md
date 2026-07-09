# Diagram Recipes (Mermaid)

Every diagram is authored as a `.mmd` file in the `diagrams/` output folder,
then rendered to `.png` by `scripts/render_diagrams.py`. Both files stay in
`diagrams/` so the user can edit the source and re-render later.

## Hard rules — renderers fail if you break these

1. A `.mmd` file contains **only Mermaid source**. No markdown code fences
   (```` ``` ````), no headings, no prose. First non-comment line is the init
   directive below; second is the diagram type.
2. Node IDs are plain identifiers (`api`, `orderFlow`) — letters, digits,
   underscores. Display text goes in the label, never in the ID.
3. Any label containing spaces, parentheses, slashes, dots, or `&` must be
   quoted: `checkout["Place order (checkout)"]`. Unquoted `(`, `)` and `&`
   are the #1 cause of render failures.
4. Use `<br/>` for line breaks inside labels, not `\n`.
5. Keep each diagram to **15 nodes or fewer** (class diagrams: ≤8 classes).
   A readable diagram beats a complete one.
6. One diagram per file.

## Standard init directive — first line of every file

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
```

## Standard palette for flowcharts

```
classDef person fill:#1F3864,stroke:#152848,color:#ffffff
classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
classDef external fill:#f5f5f5,stroke:#666666,color:#333333
classDef datastore fill:#ffe6cc,stroke:#d79b00,color:#663c00
classDef decision fill:#fff2cc,stroke:#d6b656,color:#663c00
```

---

## 01 — Context (`flowchart LR`) — for the FS

Actors on the left, the system in a subgraph, external systems on the right,
every edge labelled with what flows.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart LR
    customer(["Customer"])
    admin(["Store Admin"])
    subgraph shoplite["ShopLite System"]
        api["ShopLite<br/>Web Application"]
    end
    stripe["Stripe<br/>Payment Gateway"]

    customer -->|"Browses, orders"| api
    admin -->|"Manages catalog"| api
    api -->|"Charges cards"| stripe

    classDef person fill:#1F3864,stroke:#152848,color:#ffffff
    classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    classDef external fill:#f5f5f5,stroke:#666666,color:#333333
    class customer,admin person
    class api system
    class stripe external
```

## 02 — Feature map (`flowchart LR`) — for the FS

One subgraph per feature area (FA id in the label), one node per operation
(the FR name, not the route). Gives readers the whole functional surface on
one page.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart LR
    root["ShopLite"]
    subgraph fa1["FA-1 Order Management"]
        f11["Place order"]
        f12["Track order"]
        f13["Cancel order"]
    end
    subgraph fa2["FA-2 Catalog"]
        f21["Manage products"]
        f22["Browse and search"]
    end
    root --- fa1
    root --- fa2

    classDef system fill:#dae8fc,stroke:#6c8ebf,color:#1F3864
    classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
    class root system
    class f11,f12,f13,f21,f22 internal
```

## 03 — Business process (`flowchart TD`) — for the FS

One core process end to end, with decision diamonds for the branches the
code actually takes. Business language on every node.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
flowchart TD
    start(["Customer submits order"]) --> validate["Validate cart contents"]
    validate --> stock{"All items<br/>in stock?"}
    stock -->|no| reject["Reject with out-of-stock error"]
    stock -->|yes| charge["Charge card via Stripe"]
    charge --> ok{"Payment<br/>accepted?"}
    ok -->|no| fail["Order cancelled, customer notified"]
    ok -->|yes| persist["Order saved as Paid"]
    persist --> receipt["Receipt emailed"]
    receipt --> done(["Order placed"])

    classDef internal fill:#d5e8d4,stroke:#82b366,color:#1F3864
    classDef decision fill:#fff2cc,stroke:#d6b656,color:#663c00
    classDef external fill:#f5f5f5,stroke:#666666,color:#333333
    class validate,charge,persist,receipt internal
    class stock,ok decision
    class reject,fail external
```

## 04 — Entity lifecycle (`stateDiagram-v2`) — for the FS

Only when an entity has a status/state field. States from the enum,
transitions from the code that mutates the field, each labelled with its
cause.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
stateDiagram-v2
    [*] --> Draft : cart created
    Draft --> Placed : customer checks out
    Placed --> Paid : charge succeeds
    Placed --> Cancelled : payment fails
    Paid --> Shipped : warehouse dispatches
    Shipped --> Completed : delivery confirmed
    Cancelled --> [*]
    Completed --> [*]
```

Pitfalls: state names are identifiers (no spaces — use `PendingReview`, not
`Pending Review`); transition labels go after `:`.

## 05 — Module structure (`flowchart TB`) — for the MDS

Projects/modules and their dependency edges; data stores at the bottom.
Same recipe as a container diagram: solution subgraph, `-->|"project ref"|`
edges, palette classes (`system` for executables, `internal` for libraries,
`datastore` for databases, `external` for third parties).

## 06 — Key classes (`classDiagram`) — for the MDS

The 4–8 types that define one module's design: entry point, its interface,
the implementation, the central entity. Real member signatures, but only the
telling members — not every property.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
classDiagram
    direction LR
    class OrdersController {
        +Post(CreateOrderDto dto) IActionResult
    }
    class IOrderService {
        <<interface>>
        +PlaceOrderAsync(CreateOrderDto dto) Task~OrderResult~
    }
    class OrderService {
        -ShopContext db
        +PlaceOrderAsync(CreateOrderDto dto) Task~OrderResult~
    }
    class Order {
        +int Id
        +OrderStatus Status
        +AddLine(Product product, int quantity) void
    }
    OrdersController --> IOrderService : uses
    OrderService ..|> IOrderService : implements
    OrderService --> Order : creates
```

Pitfalls: generics use tildes (`Task~OrderResult~`, never `Task<OrderResult>`);
`<<interface>>` / `<<abstract>>` on their own line inside the class; arrows —
`-->` association, `..|>` realization, `--|>` inheritance, `o--` aggregation;
`direction LR` keeps wide diagrams compact.

## 07 — Key operation (`sequenceDiagram`) — for the MDS

Participants are the real classes from the class/module diagrams.

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
sequenceDiagram
    autonumber
    actor Customer
    participant API as OrdersController
    participant Svc as OrderService
    participant DB as ShopContext (SQL Server)

    Customer->>API: POST /api/orders
    API->>Svc: PlaceOrderAsync(dto)
    Svc->>DB: Load cart, validate stock
    Svc->>DB: SaveChanges (order + payment)
    API-->>Customer: 201 Created
```

Pitfalls: use participant aliases; `->>` call, `-->>` return; avoid `;` in
message text.

## 08 — Data model (`erDiagram`) — for the MDS

Entities from the DbContext with key attributes only (PK, FKs, 3–6 telling
fields). Attribute rows are `type name` with **single-word types** (`int`,
`string`, `datetime`, `decimal` — `decimal(18,2)` breaks the parser).

```
%%{init: {"theme": "neutral", "fontFamily": "Segoe UI, Arial, sans-serif"} }%%
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_LINE : contains
    ORDER {
        int Id PK
        int CustomerId FK
        datetime PlacedAt
        string Status
    }
```

Cardinality: `||` exactly one, `o|` zero or one, `}|` one or more, `}o` zero
or more.

---

## Render loop

After writing all `.mmd` files:

```
python "<skill>/scripts/render_diagrams.py" "<output>/diagrams"
```

If a diagram FAILs, the script prints the renderer's error naming the bad
line. Fix that `.mmd` and re-run — it re-renders everything, which is cheap.
Do not proceed to the document build until every diagram renders OK.
