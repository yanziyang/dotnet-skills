# .NET Shallow-Module Catalog

Detection heuristics, counter-signals, and the deepening move for each smell. Every entry follows the same shape:

- **Detect** — concrete signals, including grep patterns where they help. A grep hit is a *lead*, not a finding: always read the file before recording evidence.
- **Shallow because** — why the deletion test passes.
- **Counter-signals** — evidence that the pattern is justified. If a counter-signal holds, drop the finding.
- **Deepen** — the move, with a before/after sketch.

## Contents

1. [Pass-through service layer](#1-pass-through-service-layer)
2. [One-implementation interfaces](#2-one-implementation-interfaces)
3. [Generic repository over EF Core](#3-generic-repository-over-ef-core)
4. [Anemic entities, fat services](#4-anemic-entities-fat-services)
5. [MediatR/CQRS ceremony for CRUD](#5-mediatrcqrs-ceremony-for-crud)
6. [AutoMapper hiding the projection](#6-automapper-hiding-the-projection)
7. [Layer-per-project ceremony](#7-layer-per-project-ceremony)
8. [Leaky seams](#8-leaky-seams)
9. [Helper/Manager/Util wrappers](#9-helpermanagerutil-wrappers)

---

## 1. Pass-through service layer

**Detect**

- Service methods whose whole body is one call to the next layer with the same (or trivially reshaped) parameters. Grep for expression-bodied forwards: `=>\s*(await\s+)?_\w+(Repository|Repo|Service|Client)\.` — then read the class and count what fraction of its public methods are forwards.
- A service class whose constructor takes exactly one dependency and whose public methods map 1:1 onto that dependency's methods.
- Call chains like `Controller → IOrderService → OrderService → IOrderRepository → OrderRepository → DbContext` where at most one link does real work.

**Shallow because** — each layer's interface is as wide as the layer below it; understanding one operation means opening three files that say the same thing. Deleting the middle layer concentrates the logic in one place: deletion test passes.

**Counter-signals** — the service composes *multiple* dependencies per method, owns a transaction that spans repositories, or enforces authorization/invariants the endpoint can't. Then it's doing real work — keep it (and it may be the place to *absorb* the layers around it).

**Deepen** — pick one module to be deep and delete the others. Two valid directions:

- Collapse *down*: the endpoint handler talks to `DbContext` (or the domain entity) directly. Right for CRUD-heavy apps.
- Collapse *in*: the service absorbs the repository, becoming the single module that owns the operation end-to-end. Right when the operation has real logic.

```csharp
// BEFORE — three files, one operation
public class OrderService(IOrderRepository repo) : IOrderService
{
    public Task<Order?> GetOrderAsync(Guid id, CancellationToken ct)
        => repo.GetByIdAsync(id, ct);                    // forwards
}
public class OrderRepository(AppDbContext db) : IOrderRepository
{
    public Task<Order?> GetByIdAsync(Guid id, CancellationToken ct)
        => db.Orders.FirstOrDefaultAsync(o => o.Id == id, ct);   // forwards
}

// AFTER — the endpoint is the module; DbContext is the deep dependency
app.MapGet("/api/v1/orders/{id:guid}", async Task<Results<Ok<OrderResponse>, NotFound>>
    (Guid id, AppDbContext db, CancellationToken ct) =>
{
    var order = await db.Orders
        .Where(o => o.Id == id)
        .Select(o => new OrderResponse(o.Id, o.Total, o.Status))
        .FirstOrDefaultAsync(ct);
    return order is null ? TypedResults.NotFound() : TypedResults.Ok(order);
});
```

---

## 2. One-implementation interfaces

**Detect**

- For each `interface IFoo`, search for classes implementing it: grep `:\s*.*\bIFoo\b`. Exactly one implementation named `Foo` in the same assembly is the signature of a header interface.
- Check who *uses* the interface: if the only references outside the implementation are the DI registration and `Mock<IFoo>` / `Substitute.For<IFoo>()` in tests, the second "adapter" is a mock — the seam is hypothetical.
- Folders named `Interfaces/` or `Abstractions/` containing dozens of single-implementation interfaces are a bulk hit.

**Shallow because** — the interface duplicates the class's public surface line for line: zero abstraction, one more file to keep in sync. One adapter = hypothetical seam.

**Counter-signals**

- Two *runtime* implementations (e.g. `StripePayments` and `FakePayments` actually wired in dev/CI environments, not just mocked).
- The interface lives in a contracts package consumed by another team or process.
- The implementation wraps a genuinely unownable external system (SMTP, payment gateway) where a fake adapter for tests is the sane way to test — that's a real second adapter *if the fake is a maintained class*, not an ad-hoc mock setup per test.

**Deepen** — delete the interface, register the concrete class, and test through real infrastructure instead of mocks:

```csharp
// BEFORE
builder.Services.AddScoped<IOrderService, OrderService>();
// tests: var mock = new Mock<IOrderRepository>(); mock.Setup(...)  // re-implements the repo per test

// AFTER
builder.Services.AddScoped<OrderService>();
// tests: use the real DbContext against SQLite in-memory or Testcontainers —
// the test exercises the query logic the mock was hiding
```

The test change is the real win: mocked-repository tests verify that the service calls the mock; DbContext-backed tests verify the query actually works.

---

## 3. Generic repository over EF Core

**Detect**

- Grep for `interface IRepository<` / `class GenericRepository<` / `interface IUnitOfWork`.
- The tell-tale members: `GetByIdAsync`, `GetAllAsync`, `AddAsync`, `Update`, `Delete`, plus a `SaveChangesAsync` on a separate unit-of-work interface.
- Secondary evidence that the wrapper is failing: methods multiplying on derived repositories (`GetOrdersWithItemsAsync`, `GetOrdersWithItemsAndCustomerAsync`, …) or `IQueryable<T>` escaping to keep the wrapper usable (see [smell 8](#8-leaky-seams)).

**Shallow because** — `DbContext` *is* a repository and unit of work; it's one of the deepest modules in the ecosystem. The wrapper re-exposes a worse version of its interface (no `Include`, no projection, no streaming) while hiding none of its complexity. Deleting the wrapper concentrates data access on one deep, documented API.

**Counter-signals**

- A second real persistence adapter exists or is concretely planned (Dapper for hot paths, Cosmos for one aggregate). Two adapters = real seam — but then the interface should be *purpose-specific* (`IOrderQueries`), not generic.
- The codebase is a library shipped to consumers who choose their own storage.

**Deepen**

```csharp
// BEFORE — generic wrapper, then a leak to make it usable
public interface IRepository<T> where T : class
{
    Task<T?> GetByIdAsync(Guid id, CancellationToken ct);
    IQueryable<T> Query();                 // the wrapper gave up here
    Task AddAsync(T entity, CancellationToken ct);
}

// AFTER — DbContext used directly; if a seam is truly needed, make it purpose-specific
public interface IOrderQueries        // only if a second adapter actually exists
{
    Task<OrderSummary?> GetSummaryAsync(Guid id, CancellationToken ct);
    Task<IReadOnlyList<OrderSummary>> GetOpenOrdersAsync(Guid customerId, CancellationToken ct);
}
```

---

## 4. Anemic entities, fat services

**Detect**

- Entity classes that are all `{ get; set; }` auto-properties with public setters and no methods.
- Services enforcing invariants with if-throw sequences before mutating those properties. Grep entity property mutations across service files: the same `order.Status =` appearing in several services means the invariant lives nowhere.
- The same validation repeated in multiple services (or a service and a validator) for one entity.

**Shallow because** — the entity's interface (every property settable by anyone) is maximally wide while it does nothing; locality is destroyed because the rules about an `Order` live in `OrderService`, `RefundService`, and `AdminService`.

**Counter-signals** — DTOs, EF query projections, and records crossing the wire are *supposed* to be dumb; this smell only applies to domain entities that have invariants. If the app is honest CRUD with no invariants beyond field validation, there is no finding.

**Deepen** — move each invariant to the entity; give it real methods and constructors, make setters private. Services shrink to orchestration.

```csharp
// BEFORE — invariant scattered in services
if (order.Status != OrderStatus.Open) throw new InvalidOperationException("...");
if (order.Items.Count == 0) throw new InvalidOperationException("...");
order.Status = OrderStatus.Submitted;   // repeated, slightly differently, in 3 services

// AFTER — the entity owns its rules; illegal states unrepresentable at the call site
public class Order
{
    public OrderStatus Status { get; private set; }
    private readonly List<OrderItem> _items = [];

    public void Submit()
    {
        if (Status != OrderStatus.Open) throw new InvalidOperationException("Only open orders can be submitted.");
        if (_items.Count == 0) throw new InvalidOperationException("Cannot submit an empty order.");
        Status = OrderStatus.Submitted;
    }
}
```

---

## 5. MediatR/CQRS ceremony for CRUD

**Detect**

- `MediatR` in `PackageReference`s; grep `IRequestHandler<` and sample a handful of handlers.
- Handlers under ~10 lines that do exactly what a pass-through service does: forward to `DbContext` or a repository.
- Check `Program.cs` for pipeline behaviors (`IPipelineBehavior<,>` registrations). None, or behaviors that duplicate ASP.NET middleware (logging, validation that `AddValidation()`/endpoint filters already do), strengthens the finding.
- Count the files per operation: `CreateOrderCommand.cs` + `CreateOrderHandler.cs` + `CreateOrderValidator.cs` + DTO for one INSERT.

**Shallow because** — the mediator inserts a seam (request type ↔ handler) with exactly one adapter per request, ever. Dispatch is indirect (go-to-definition lands on `IRequestHandler`, not the code), and the "decoupling" decouples an endpoint from the one handler it exists to call.

**Counter-signals**

- Pipeline behaviors carrying real cross-cutting leverage that middleware can't express (per-request transactions with domain-event dispatch, idempotency keyed on the request type).
- Handlers invoked from *multiple* entry points (HTTP + message consumer + scheduled job) — that's real leverage on the request contract.

**Deepen** — the Minimal API handler is already a routable, DI-injected, testable unit. Call the operation directly:

```csharp
// BEFORE — 3 files + reflection dispatch for one query
public record GetOrderQuery(Guid Id) : IRequest<OrderResponse?>;
public class GetOrderHandler(AppDbContext db) : IRequestHandler<GetOrderQuery, OrderResponse?> { /* 5 lines */ }
app.MapGet("/api/v1/orders/{id:guid}", (Guid id, IMediator m, CancellationToken ct)
    => m.Send(new GetOrderQuery(id), ct));

// AFTER — one place, statically dispatched
app.MapGet("/api/v1/orders/{id:guid}", async Task<Results<Ok<OrderResponse>, NotFound>>
    (Guid id, AppDbContext db, CancellationToken ct) => { /* the same 5 lines */ });
```

If the codebase is huge, propose the deepening for *new* code plus opportunistic migration, not a big-bang rewrite.

---

## 6. AutoMapper hiding the projection

**Detect**

- `AutoMapper` in `PackageReference`s; grep `CreateMap<` and `\.Map<`.
- The damaging variant: `_mapper.Map<OrderDto>(entity)` *after* materializing full entities — meaning the SQL fetched every column and every `Include`, then mapping happened in memory. Grep for `ToListAsync()` followed by `Map<` in the same method.
- Mapping configuration errors that only surface at runtime (`ForMember` chains, `AssertConfigurationIsValid` in tests as a patch over the compiler).

**Shallow because** — the profile is an interface a reader must learn (which members map, which are ignored, what conventions apply) to understand a transformation that C# expresses directly with compile-time checking. Locality is lost: the mapping lives in a `Profiles/` folder far from both the query and the DTO.

**Counter-signals** — dozens of large DTOs that genuinely mirror entities 1:1, where the team runs `ProjectTo<T>` (so EF still translates to SQL) and keeps profiles next to the DTOs. Mediocre but functioning; only flag it if mapping bugs or over-fetching are actually observable.

**Deepen** — explicit projection inside the query. The compiler checks it and EF translates it:

```csharp
// BEFORE — full entity + Includes materialized, then mapped in memory
var order = await db.Orders.Include(o => o.Items).FirstOrDefaultAsync(o => o.Id == id, ct);
return _mapper.Map<OrderResponse>(order);

// AFTER — SQL selects exactly the DTO's columns; rename a property and this line fails to compile
var order = await db.Orders
    .Where(o => o.Id == id)
    .Select(o => new OrderResponse(o.Id, o.Total, o.Items.Count))
    .FirstOrDefaultAsync(ct);
```

---

## 7. Layer-per-project ceremony

**Detect**

- Solution shape: `X.Domain`, `X.Application`, `X.Infrastructure`, `X.Api` (or `Core`/`Data`/`Web`) with references in a straight line.
- One or more projects containing fewer than ~10 files, mostly interfaces and DTOs — count files per project during the solution map.
- Cross-project ping-pong to follow one request: endpoint in `Api`, interface in `Application`, implementation in `Infrastructure`, entity in `Domain`.

**Shallow because** — a project boundary is the heaviest interface .NET has (assembly, package refs, `InternalsVisibleTo` gymnastics), and here it encloses almost no implementation. The layering usually *duplicates* the smells above: the `Application`/`Infrastructure` split exists to hold the one-implementation interfaces and the repository wrappers.

**Counter-signals**

- A project with a real second consumer: shared contracts referenced by another service, a domain package used by both an API and a worker process.
- Genuinely separate deployables.
- Team boundaries that the projects enforce on purpose.

**Deepen** — collapse to the few projects with real boundaries (often: one app project + one test project; sometimes + one contracts project). Namespaces and folders provide organization; projects should mark deployment or consumption seams only. Grade this **Speculative** or **Worth exploring** unless the projects are nearly empty — it's a design conversation, not a mechanical edit.

---

## 8. Leaky seams

A seam exists (interface, layer, project boundary) but the abstraction escapes through it — worst of both worlds: indirection cost paid, encapsulation not received.

**Detect**

- `IQueryable<T>` in any interface or public return type of a "repository": grep `IQueryable<` in interface declarations. The caller now composes SQL through the seam; the repository hides nothing.
- EF entities returned from endpoints (serializing lazy-load proxies, exposing every column). Cross-check endpoint return types against the DbContext's entity types.
- `DbContext` injected on *both* sides of a seam — controllers using it directly while services/repositories also wrap it. The seam claims data access is encapsulated; usage disproves it.
- Domain project with EF Core package references while an Infrastructure project claims to own persistence.

**Shallow because** — callers depend on everything behind the seam anyway, so the interface is as wide as the implementation. Any refactor behind the seam breaks callers; the seam provides zero leverage.

**Counter-signals** — essentially none for entities-on-the-wire. For `IQueryable`, a deliberate, documented specification/OData-style composition layer counts as a design choice — flag it only if it's clearly accidental.

**Deepen** — either close the seam (return materialized DTOs, keep queries inside the module) or delete it (admit the endpoint owns its query, per smell 1/3). Both are honest; straddling is not.

---

## 9. Helper/Manager/Util wrappers

**Detect**

- Grep class names: `class \w*(Helper|Manager|Util|Utils|Utility|Wrapper|Provider)\b`, then read them.
- Methods that forward 1:1 to a BCL or framework API: `DateTimeHelper.GetUtcNow()` over `TimeProvider`/`DateTimeOffset.UtcNow`, `JsonHelper.Serialize(x)` over `JsonSerializer.Serialize(x)`, `FileHelper.ReadAllText` over `File.ReadAllText`.
- `StringExtensions`-style grab bags where each method is used from one call site.

**Shallow because** — one more name for the same operation; readers must open the wrapper to learn it does nothing. Deleting it and calling the BCL inline concentrates nothing *and* scatters nothing — but it removes an interface, which is a pure win.

**Counter-signals**

- The wrapper adds a real policy: `JsonHelper` that pins the app-wide `JsonSerializerOptions` is a deep one-liner — keep it (though prefer configuring options once in DI).
- Time abstraction for testability: prefer the BCL's `TimeProvider` (.NET 8+) over a custom `IDateTimeProvider` — if you find the custom one, the finding is "replace with `TimeProvider`", not "delete".

**Deepen** — inline the BCL call, or replace the custom abstraction with the platform one (`TimeProvider`, `IOptions<JsonSerializerOptions>`). These are usually **Strong** but small; bundle several into one candidate card ("delete 5 shallow wrappers") rather than spending a card on each.

---

## Reinforcement map

Findings that co-occur amplify each other — say so in the report, because the combined candidate is stronger than its parts:

- Smells **1 + 2 + 3** almost always travel together: pass-through service, behind a one-implementation interface, over a generic repository. The combined deepening ("endpoint → DbContext, delete two layers and four interfaces") is one **Strong** candidate, not three medium ones.
- Smell **5** (MediatR ceremony) usually contains smell **1** inside each handler.
- Smell **7** (layer projects) is often just smells 2 and 3 given their own `.csproj` files — collapse the modules first; the project collapse may become trivial afterwards.
