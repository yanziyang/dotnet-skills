# .NET Discovery Guide

How to scan a .NET 8–10 repository and turn files into architecture facts.
Work through the sections in order. Every fact you record here feeds a
specific doc: the "feeds" column tells you where it lands.

## 1. Solution shape

Enumerate with `git ls-files` (respects .gitignore) rather than raw globbing:

```
git ls-files "*.sln" "*.slnx" "*.csproj" "*.props" "*.targets" "global.json"
```

| File | What it tells you | Feeds |
|---|---|---|
| `*.sln` / `*.slnx` | Project inventory. `.slnx` (XML solution format) implies recent tooling (.NET 9+ SDK era) | ProjectStructure |
| `*.csproj` — `<TargetFramework>` | Platform: `net8.0`, `net9.0`, `net10.0` (LTS: 8 and 10). Multi-targeting shows as `<TargetFrameworks>` | ProjectStructure, KnowledgeBase, JSON `tech_stack` |
| `*.csproj` — `Sdk="..."` attribute | `Microsoft.NET.Sdk.Web` = web app/API; `.Worker` = background service; `.Razor` = component lib; plain `Microsoft.NET.Sdk` + `<OutputType>Exe` = console; no OutputType = class library | ProjectStructure |
| `*.csproj` — `<ProjectReference>` | The dependency graph. Record every edge — this is the Architecture.md container diagram | Architecture |
| `Directory.Build.props` | Solution-wide settings: `LangVersion`, `Nullable`, `TreatWarningsAsErrors`, analyzers | DevelopmentGuide |
| `Directory.Packages.props` | Central Package Management (CPM) — the single source of package versions. If present, read versions here, not in csproj files | KnowledgeBase |
| `global.json` | Pinned SDK version — a build prerequisite | DevelopmentGuide |
| `.config/dotnet-tools.json` | Local tools (`dotnet ef`, `dotnet format`, …) — needed for `dotnet tool restore` | DevelopmentGuide |
| Test csproj (`xunit`/`NUnit`/`MSTest`/`TUnit` package, or `<IsTestProject>`) | Test projects — count them and note the framework | DevelopmentGuide, TechnicalDebt (if none) |

An `*.AppHost` project referencing `Aspire.Hosting.*` is a **.NET Aspire**
orchestrator: its `AppHost.cs`/`Program.cs` declares every service, database,
and container the system runs — read it early, it is a map of the whole
architecture.

## 2. Packages are architecture evidence

Read package references (from `Directory.Packages.props` if CPM, else each
csproj). Each row you match implies a fact to verify and document:

| Package(s) | Implies | Verify by reading |
|---|---|---|
| `Microsoft.EntityFrameworkCore.SqlServer` / `.Npgsql...PostgreSQL` / `.Sqlite` / `Pomelo...MySql` | Relational DB + which engine | the `DbContext`, `Migrations/`, connection strings |
| `Dapper` | Raw-SQL data access (possibly alongside EF) | classes with `IDbConnection` usage |
| `MongoDB.Driver`, `StackExchange.Redis`, `Microsoft.Extensions.Caching.Hybrid` | Document store / cache layer | registration in Program.cs |
| `MediatR` | In-process CQRS/mediator pattern | handlers folder, pipeline behaviors |
| `FluentValidation` | Validation layer | validator classes, where they're wired |
| `AutoMapper` / `Mapster` | DTO mapping layer | profiles/configs |
| `Serilog.*`, `OpenTelemetry.*` | Structured logging / distributed tracing | logging config in Program.cs + appsettings |
| `MassTransit`, `NServiceBus`, `Rebus`, `Confluent.Kafka`, `RabbitMQ.Client`, `Azure.Messaging.ServiceBus` | Message bus — an Integration feature per consumer/producer | consumer classes, topology config |
| `MQTTnet` | MQTT (IoT) integration — topics are entry points | topic subscriptions/publishes |
| `Grpc.AspNetCore` | gRPC services | `.proto` files, `MapGrpcService` calls |
| `Microsoft.AspNetCore.SignalR.*` or `MapHub<` in code | Real-time hub endpoints | hub classes |
| `Hangfire.*`, `Quartz.*` | Scheduled/background jobs — Infrastructure features | job classes, cron expressions |
| `Polly`, `Microsoft.Extensions.Http.Resilience` | Resilience policies on outbound calls | named policies, `AddResilienceHandler` |
| `Refit`, typed `AddHttpClient<...>` | Outbound HTTP integrations — one Integration feature each | client interfaces, base URLs in config |
| `Microsoft.AspNetCore.Authentication.JwtBearer`, `Microsoft.Identity.Web`, `OpenIddict.*`, `Duende.IdentityServer` | Auth scheme (record which!) | auth setup in Program.cs |
| `Microsoft.AspNetCore.OpenApi`, `Swashbuckle.*`, `NSwag.*` | API docs endpoint (`/openapi/v1.json` is built-in style on .NET 9/10) | Program.cs |
| `Aspire.*` | .NET Aspire orchestration / service defaults | AppHost + ServiceDefaults projects |
| `Azure.*`, `AWSSDK.*`, `Google.Cloud.*` | Cloud service dependencies — Integration features | usage sites + config keys |
| `Testcontainers.*`, `Microsoft.AspNetCore.Mvc.Testing`, `Respawn` | Integration-test infrastructure | test fixtures |
| `Microsoft.Playwright`, `Selenium.*` | E2E/UI tests | test project |

Packages you don't recognise: note name + version in ProjectStructure.md and
move on — do not speculate about what they do.

## 3. Composition root

For each executable project read `Program.cs` (plus `Startup.cs` and any
`*Extensions.cs` it calls, e.g. `AddApplicationServices()` — follow those
calls, the registrations inside them count).

Record three lists:

1. **Service registrations** — `builder.Services.Add...` lines. Singleton
   registrations of clients/managers are usually Reusable Components;
   `AddScoped<IFoo, Foo>` pairs enumerate the service layer.
2. **Middleware pipeline in order** — `app.Use...` sequence matters
   (auth before authorization, exception handler first). Copy the order
   into Architecture.md.
3. **Hosted services** — `AddHostedService<T>` / `BackgroundService`
   subclasses. Each is an Infrastructure or Integration feature.

## 4. Entry points (feature evidence)

A feature = entry point + traced implementation. Find entry points with:

| Search for | Entry point kind |
|---|---|
| `[ApiController]` classes, `[Http*]` attributes | Controller endpoints |
| `Map(Get\|Post\|Put\|Patch\|Delete)\|MapGroup` | Minimal API endpoints (the .NET 8+ default style) |
| `MapHub<`, `MapGrpcService<` | SignalR / gRPC |
| `IConsumer<T>` (MassTransit), `IHandleMessages<T>` (NServiceBus/Rebus), Kafka consume loops | Message consumers |
| `BackgroundService`, `IHostedService`, `[Quartz] IJob`, Hangfire `RecurringJob` | Background/scheduled work |
| `ManagedMqttClient`/`SubscribeAsync` topic strings | MQTT topics |
| Blazor `.razor` pages with `@page`, MVC Views, MAUI pages | UI surfaces |
| `System.CommandLine` / verb parsing in console apps | CLI commands |

For every endpoint record: route/verb (or topic/queue), auth requirement
(`[Authorize]`, `RequireAuthorization()`, policy name), handler
class/method, and one sentence of what it does after reading the handler.

## 5. Data layer

- Every `DbContext` subclass: its `DbSet<>` properties are the entity list;
  `OnModelCreating` + `IEntityTypeConfiguration<>` classes give keys and
  relationships → `DataModel.md` er-diagram.
- `Migrations/` folder: latest migration name + date shows schema currency.
  `EnsureCreated()` instead of `Migrate()` is a technical-debt flag for
  anything beyond a prototype.
- Connection strings: names and providers from `appsettings*.json` (record
  the *key names*, never copy credential values into docs).
- Non-EF stores: Redis usage, blob containers, file paths, MongoDB
  collections.

## 6. Configuration & environments

- Diff `appsettings.json` vs `appsettings.Development.json` /
  `appsettings.Production.json` — environment differences are deployment
  facts.
- Strongly-typed options: `AddOptions<T>` / `Configure<T>` / classes bound
  with `Bind()` — list them in DevelopmentGuide with their section names.
- `<UserSecretsId>` in csproj → local dev uses user secrets; say so in
  DevelopmentGuide.
- `launchSettings.json` → local URLs, ports, environment variables.
- **Never copy secret values into documentation.** Key names only. If a
  real-looking secret is committed in appsettings, record it as Critical
  technical debt.

## 7. Tests, CI/CD, deployment

| Evidence | Record |
|---|---|
| Test projects + frameworks | How to run (`dotnet test`), what's covered; missing coverage for core features → TechnicalDebt |
| `.github/workflows/*.yml`, `azure-pipelines.yml`, `.gitlab-ci.yml` | Build/test/deploy pipeline summary for DevelopmentGuide |
| `Dockerfile`, `docker-compose*.yml` | Container story: base images, exposed ports, service dependencies |
| K8s manifests / Helm / Bicep / Terraform | Deployment target for Architecture.md deployment section |
| Aspire AppHost | Local orchestration (run with `dotnet run --project *.AppHost`); resources declared = deployment shape |

## 8. Version-specific notes (.NET 8 → 10)

Only record platform facts you can evidence, but know what to look for:

- **.NET 10 / C# 14**: `field` keyword in properties, extension members
  (`extension(...)` blocks), minimal-API validation via `AddValidation()`,
  `.slnx` solutions. LTS release.
- **.NET 9 / C# 13**: `HybridCache`, built-in OpenAPI document generation
  (`AddOpenApi`/`MapOpenApi`), `params` collections. STS release.
- **.NET 8 / C# 12**: primary constructors, collection expressions,
  `TimeProvider`, keyed DI services (`AddKeyedScoped`). LTS release.

If the TFM is older than `net8.0`, flag "upgrade to a supported LTS" as a
P1 backlog item (out of support).

## 9. Skip list

Never read or document: `bin/`, `obj/`, `node_modules/`, `dist/`, `build/`,
`.git/`, `packages/`, `TestResults/`, `artifacts/`, `*.g.cs`,
`*.Designer.cs`, `*.generated.cs`, `Migrations/*.Designer.cs` bodies,
minified assets, lock files (note their existence only).
