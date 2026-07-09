# dotnet-skills

Agent skills for .NET projects (ASP.NET Core on .NET 8–10). Designed to be consumed by coding agents — instructions are prescriptive and code samples are complete, so they work well with mid-tier models.

## Skills

| Skill | Description |
|-------|-------------|
| [architecture-design-document](skills/architecture-design-document/SKILL.md) | Scan an entire .NET repository and generate a professional Architecture Design Document as a Word (.docx) file — cover page, TOC, evidence-based content — illustrated with rendered diagrams (context, container, component, sequence, ER, deployment) whose editable sources (Mermaid `.mmd` + draw.io) are exported to a `diagrams/` subfolder. Bundles Python scripts for docx assembly, Mermaid→PNG rendering, and draw.io generation. |
| [api-design](skills/api-design/SKILL.md) | REST API design patterns for ASP.NET Core: resource naming, status codes, `TypedResults`, RFC 9457 ProblemDetails error responses, validation, pagination, filtering, versioning (`Asp.Versioning`), and rate limiting. |
| [fs-mds-document](skills/fs-mds-document/SKILL.md) | Scan an entire .NET repository and generate a Functional Specification (FS) and Module Design Specification (MDS) as professional Word (.docx) documents — feature areas with FR/BR IDs, per-module designs, cross-document traceability — illustrated with rendered diagrams (context, feature map, process, state, module structure, class, sequence, ER) whose editable sources (Mermaid `.mmd` + draw.io) are exported to a `diagrams/` subfolder. |
| [data-dictionary-document](skills/data-dictionary-document/SKILL.md) | Generate a professional Data Dictionary as a Word (.docx) document from a database's DDL (SQL scripts, database projects, or EF Core migrations), enriched by scanning the .NET codebase for what each table and column means — with Entity Relationship Diagrams broken down by module for large schemas, whose editable sources (Mermaid `.mmd` + native draw.io entity shapes) are exported to a `diagrams/` subfolder. |
| [presentation-slides](skills/presentation-slides/SKILL.md) | Scan an entire .NET repository and generate a professional 16:9 PowerPoint (.pptx) presentation — audience-tailored for new team members, management, or customers, with speaker notes — illustrated with rendered diagrams (context, container, sequence, ER, deployment) whose editable sources (Mermaid `.mmd` + draw.io) are exported to a `diagrams/` subfolder. Bundles Python scripts for deterministic pptx assembly from a content-only `deck.json`, Mermaid→PNG rendering, and draw.io generation. |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | Systematically diagnose and fix bugs — build a red/green feedback loop first (eight .NET loop recipes: xUnit repro, `WebApplicationFactory`, HTTP script, console harness, `git bisect run`, flaky-bug amplification, determinism pinning), then test ranked falsifiable hypotheses with tagged instrumentation and `dotnet-*` diagnostics, and finish with a watched-red regression test and traceless cleanup. Includes a symptom→cause catalog of ~30 common .NET root causes. |
| [code-review](skills/code-review/SKILL.md) | Review C#/.NET code changes for correctness, async/threading, EF Core, security, resource-lifetime, and API-contract defects — verified against an evidence gate and presented as a visual HTML report with severity badges, before/after code, and a mechanical verdict. |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | Scan a .NET solution for architectural deepening opportunities — pass-through layers, one-implementation interfaces, generic repositories over EF Core, MediatR ceremony, anemic entities — and present them as a visual HTML report with before/after diagrams. |
| [maintain-knowledge](skills/maintain-knowledge/SKILL.md) | Create and maintain a living markdown knowledge base in `Documentation/` — project structure, architecture with Mermaid diagrams, feature inventory, data model, development guide, technical debt, and improvement backlog for humans, plus an agent-optimised `KnowledgeBase.md` and machine-readable `PROJECT_KNOWLEDGE.json` for coding agents. Safe to re-run: incremental updates via git diff, stable section merge rules, and a verification gate. |

## Structure

Each skill follows the [Agent Skills](https://code.claude.com/docs/en/skills) layout:

```
skills/<skill-name>/
├── SKILL.md          # frontmatter (name, description) + core guidance
├── references/       # deeper topic files, loaded on demand
└── scripts/          # (optional) bundled executables the agent runs as-is
```

## Usage

### Install from this repository

**Option 1: Using `npx skills` (recommended)**

Install skills directly from the GitHub repository into your project:

```bash
npx skills install https://github.com/yanziyang/dotnet-skills
```

This downloads all skills and installs them into `.claude/skills/`. You can also install individual skills:

```bash
npx skills install https://github.com/yanziyang/dotnet-skills --skill diagnosing-bugs
npx skills install https://github.com/yanziyang/dotnet-skills --skill code-review
```

**Option 2: Manual installation**

Clone the repo and copy individual skill folders:

```bash
git clone https://github.com/yanziyang/dotnet-skills.git
cp -r dotnet-skills/skills/<skill-name> <your-project>/.claude/skills/
```

### How skills work

Copy a skill folder into your project's `.claude/skills/` directory (or your agent platform's skills location). The agent loads `SKILL.md` when the task matches the skill's description and pulls in reference files as needed.

Each skill is self-contained — all files in the skill folder (references, scripts) are included, so no additional dependencies or setup are required.
