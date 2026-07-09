# Deck Outline — storyline and audience tailoring

A good solution-overview deck answers, in order: *what is this system, who
uses it, how is it built, how well is it run, and what happens next.* Build
the deck from this skeleton, then apply the audience adjustments below.

## Standard storyline (14–18 slides)

| # | Type | Slide |
|---|------|-------|
| 1 | `title` | Solution name + one-line value statement, date, team |
| 2 | `bullets` | Agenda — the 3–4 sections of the deck |
| 3 | `section` | **01 — What is \<System\>?** |
| 4 | `bullets` | The elevator pitch: problem, users, what the system does |
| 5 | `image` | System context diagram (`01-system-context.png`) |
| 6 | `cards` | Key capabilities (from the actual HTTP surface / features) |
| 7 | `stats` | The solution at a glance: projects, endpoints, entities, framework |
| 8 | `section` | **02 — How it's built** |
| 9 | `cards` or `table` | Technology stack (framework, data, messaging, auth, logging) |
| 10 | `image` | Container / project structure diagram (`02-container.png`) |
| 11 | `image_bullets` | The key runtime flow (sequence diagram + talking points) |
| 12 | `image` | Data model (`04-data-model.png`) — skip if no DbContext |
| 13 | `image` or `bullets` | Deployment & operations (`05-deployment.png`) |
| 14 | `section` | **03 — Working with it** / **Where it's headed** |
| 15 | `bullets` or `stats` | Quality: tests, CI/CD, logging, known gaps — honestly |
| 16 | `two_column` or `timeline` | Getting started / roadmap (see audience notes) |
| 17 | `closing` | Thank you, repo link, contacts |

Skip any slide the repo gives you no material for; never pad. A 12-slide
deck grounded in evidence beats an 18-slide deck with filler.

## Audience adjustments

Ask which audience the deck is for only if the user hasn't said and the
choice would really change the deck; otherwise default to **new team
members** (the most common request) and note the assumption when delivering.

### New team members (default)
Goal: productive in week one. Keep every technical slide. Slide 16 becomes
**Getting started** (`two_column`): left column "Run it locally" (clone,
`dotnet run`, connection string, seeded logins — from README/launchSettings),
right column "Where things live" (which project to touch for which kind of
change, test conventions). Add a `bullets` slide on code conventions if the
repo shows clear ones (folder-per-feature, CQRS handlers, etc.).

### Management
Goal: confidence and decisions, not mechanics. Drop the data-model and
component-level slides; keep context diagram, capabilities, stats, and a
simplified container view. Expand slide 15 into risks/technical debt with
business impact ("no automated tests means every release needs manual QA").
Slide 16 becomes a `timeline` roadmap; if the repo has no roadmap evidence
(TODOs, issues, ADRs), propose one clearly labelled as a recommendation.
Bullets carry outcomes ("orders are confirmed in under a second"), not
technology names.

### Customers
Goal: trust in the product. Only the context diagram — internal structure is
not their business. Lead with capabilities (`cards`) phrased as benefits,
then reliability/security evidence (auth, encryption, backups, uptime
mechanisms actually found in the repo). No project names, no code identifiers,
no internal risks. Closing slide invites follow-up rather than listing repo
links.

If the user wants more than one audience, build one deck per audience —
sharing diagrams from the same `diagrams/` folder — rather than one deck
that serves nobody.
