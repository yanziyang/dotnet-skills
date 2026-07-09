# Data Dictionary — document template

Write `<output>/data-dictionary.md` following this skeleton, then build it
with `scripts/build_docx.py`. The builder understands headings 1–4, pipe
tables, bullet/numbered lists, `![caption](path)` images (auto-numbered
figures), `**bold**` / `*italic*` / `` `code` `` spans, fenced code blocks,
and `> callout` lines. Frontmatter drives the cover page.

Column tables are wide — keep cell text terse so rows don't wrap into
unreadable stacks. Notation like PK/FK/`†` is defined once in the legend,
then used without explanation.

## Frontmatter

```
---
title: <SolutionName> Data Dictionary
subtitle: Database Reference Documentation
project: <SolutionName>
version: 1.0
date: <today, e.g. 9 July 2026>
author: Generated from repository and DDL analysis
status: Draft
---
```

## Skeleton

```markdown
# 1. Introduction

## 1.1 Purpose
One paragraph: what this document is (authoritative column-level reference
for the <name> database) and who uses it (developers, DBAs, analysts).

## 1.2 Sources
| Source | Detail |
|--------|--------|
| DDL | <file(s) analyzed, e.g. db/schema.sql, 12 CREATE TABLE statements> |
| Code | <DbContext / entity classes / configurations read for descriptions> |
| Documentation | <README, docs/ files that informed descriptions> |
State the DBMS and version/dialect the DDL targets (e.g. SQL Server 2022)
and how that was determined.

## 1.3 Notation
| Mark | Meaning |
|------|---------|
| PK | Primary key column |
| FK | Foreign key column (references shown in the Keys table) |
| UK | Unique constraint / unique index member |
| Null = Yes | Column accepts NULL |
| † | Description inferred from naming and code usage — not stated in DDL comments, code, or docs |

# 2. Database Overview

## 2.1 Summary
Table counts, schemas, naming conventions actually observed (e.g. "tables
are singular PascalCase; every table has an int identity PK named Id"),
plus global patterns: audit columns, soft-delete flags, concurrency tokens.

## 2.2 Entity Relationship Overview
![Module overview](diagrams/00-erd-overview.png)
(With ≤ 12 tables there is no overview diagram — put the single full ERD
here instead and omit chapter 3's per-module diagrams.)

## 2.3 Modules
| Module | Tables | Description |
|--------|--------|-------------|
Every table appears in exactly one module row — the reader uses this to
find the table's section.

# 3. <Module Name>            <- one chapter per module, repeat as needed

One short paragraph: what this module stores and which features use it.

![<Module> ERD](diagrams/01-erd-<module>.png)

## 3.1 <schema>.<TableName>   <- one section per table, in FK-dependency
                                 order (parents before children)

Purpose: 1–3 sentences. What one row represents, which code writes/reads it
(name the class), lifecycle notes (append-only, soft-deleted, seeded).

**Columns**

| # | Column | Type | Null | Default | Key | Description |
|---|--------|------|------|---------|-----|-------------|
| 1 | Id | int | No | IDENTITY | PK | Surrogate key. |
| 2 | CustomerId | int | No | — | FK | Owning customer; see Keys. |
| 3 | Status | nvarchar(20) | No | 'Placed' | | Order state machine value: Placed, Paid, Shipped, Cancelled.† |

Every column from the DDL appears, in DDL order, with its exact type. The
Description cell is never empty: use DDL comments / EF `HasComment` / XML
docs / validation attributes when they exist; otherwise infer from naming
and usage and append †. Enumerated values: list them if the code defines
them (name the enum).

**Keys & Constraints**

| Constraint | Type | Definition |
|------------|------|------------|
| PK_Order | Primary key | (Id) |
| FK_Order_Customer | Foreign key | CustomerId → Customer(Id), ON DELETE CASCADE |
| CK_Order_Total | Check | Total >= 0 |

**Indexes** (omit the table if the DDL defines none beyond the PK)

| Index | Columns | Unique | Notes |
|-------|---------|--------|-------|
| IX_Order_CustomerId | CustomerId | No | FK lookup |

Include triggers and computed-column definitions here as extra rows or a
short paragraph when the DDL has them — they are behavior a reader cannot
see from the columns alone.

# 4. Relationship Reference

Every foreign key in one flat table — the cross-module lookup companion to
the per-module ERDs.

| Child table | FK column(s) | Parent table | On delete | Cardinality |
|-------------|--------------|--------------|-----------|-------------|

# 5. Reference Data
Seed/lookup rows found in the DDL (INSERT statements), EF `HasData` calls,
or seeders — per table: the values and what they mean. Omit the chapter if
none exist, and say so in 2.1.

# Appendix A. Glossary
Domain terms used in descriptions, with the table(s) where each lives.
```

## Quality bar

- **Complete or flagged**: every table in the DDL gets a section; every
  column gets a row. If something in the DDL is ambiguous (a column no code
  references, an unused table), document it and mark it honestly
  ("no usage found in the codebase").
- **Exact types**: copy types, defaults, and constraint definitions from the
  DDL verbatim — this document is what people consult *instead of* the DDL.
- **Grounded descriptions**: name the evidence in descriptions where it
  helps ("set by `OrderService.PlaceOrderAsync`"); mark inference with †.
- **No invention**: never document tables, columns, or constraints that are
  not in the DDL, even if entity classes suggest they exist — note such
  drift in 2.1 instead (it is a real finding).
