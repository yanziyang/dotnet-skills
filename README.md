# dotnet-skills

Agent skills for .NET projects (ASP.NET Core on .NET 8–10). Designed to be consumed by coding agents — instructions are prescriptive and code samples are complete, so they work well with mid-tier models.

## Skills

| Skill | Description |
|-------|-------------|
| [architecture-design-document](skills/architecture-design-document/SKILL.md) | Scan an entire .NET repository and generate a professional Architecture Design Document as a Word (.docx) file — cover page, TOC, evidence-based content — illustrated with rendered diagrams (context, container, component, sequence, ER, deployment) whose editable sources (Mermaid `.mmd` + draw.io) are exported to a `diagrams/` subfolder. Bundles Python scripts for docx assembly, Mermaid→PNG rendering, and draw.io generation. |
| [api-design](skills/api-design/SKILL.md) | REST API design patterns for ASP.NET Core: resource naming, status codes, `TypedResults`, RFC 9457 ProblemDetails error responses, validation, pagination, filtering, versioning (`Asp.Versioning`), and rate limiting. |
| [code-review](skills/code-review/SKILL.md) | Review C#/.NET code changes for correctness, async/threading, EF Core, security, resource-lifetime, and API-contract defects — verified against an evidence gate and presented as a visual HTML report with severity badges, before/after code, and a mechanical verdict. |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | Scan a .NET solution for architectural deepening opportunities — pass-through layers, one-implementation interfaces, generic repositories over EF Core, MediatR ceremony, anemic entities — and present them as a visual HTML report with before/after diagrams. |

## Structure

Each skill follows the [Agent Skills](https://code.claude.com/docs/en/skills) layout:

```
skills/<skill-name>/
├── SKILL.md          # frontmatter (name, description) + core guidance
├── references/       # deeper topic files, loaded on demand
└── scripts/          # (optional) bundled executables the agent runs as-is
```

## Usage

Copy a skill folder into your project's `.claude/skills/` directory (or your agent platform's skills location). The agent loads `SKILL.md` when the task matches the skill's description and pulls in reference files as needed.
