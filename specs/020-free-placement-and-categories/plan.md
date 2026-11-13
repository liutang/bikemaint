# Implementation Plan: 020 Free Part Placement and a Categorised Part Palette

**Branch**: `020-free-placement-and-categories` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

Remove the placement rules and the one-per-kind-per-parent limit, and replace the flat palette with five collapsible categories listing exactly the 34 parts the rider supplied. The part catalog (`app/models/component_kinds.py`) gains display names and categories and loses its rules; services keep only the "not inside itself or its own sub-tree" check; the palette and drop targets stop filtering by kind.

## Technical Context

**Language/Version**: Python 3 (CPython 3.13)

**Primary Dependencies**: FastAPI, Jinja2, HTMX (unchanged); `app/static/builder.js` (existing vanilla JS asset)

**Storage**: SQLite; `component.component_type` is free TEXT with no constraint, so **no migration**

**Testing**: pytest (`tests/models`, `tests/services`, `tests/routers`, `tests/test_ui_*`)

**Target Platform**: Self-hosted container (unchanged)

**Project Type**: web-service (single FastAPI app)

**Performance Goals**: Palette is static (34 items); no measurable change to page cost

**Constraints**: No new JS framework; categories use native `<details>`/`<summary>` (keyboard operable, state announced by the browser); all closed on load, no persistence

**Scale/Scope**: One rider; tens of parts per bike

## Constitution Check (v1.3.0)

| Principle | Result | Notes |
|---|---|---|
| I Simplicity | Pass | Deleting rules and the per-kind limit removes code; native `<details>` instead of JS |
| II Modular design | Pass | Catalog stays pure reference data in `app/models/`; services hold the cycle check; templates only render |
| III TDD | Pass (planned) | Each task is test-first; tests asserting the old rules are rewritten before code changes |
| IV Security | Pass | Server still validates every request: type must be an offered kind; self/descendant check stays server-side, not just in JS |
| V Observability | Pass | No new failure paths beyond existing logged moves |
| Stack / layout | Pass | No new dependency, directory or script |

## Project Structure

### Documentation (this feature)

```text
specs/020-free-placement-and-categories/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ui-contract.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
app/
├── models/
│   ├── component_kinds.py       # catalog: type, name, category, offered; no placement rules, no multi flag
│   └── requests.py              # drop MULTI_INSTANCE import; type validation uses the new catalog
├── services/
│   ├── component_service.py     # drop placement/nesting-conflict checks, keep self/descendant check; targets = every slot
│   └── builder_service.py       # palette grouped by category, all kinds always; nodes accept everything
├── routers/
│   ├── components.py            # type choice lists all offered kinds; drop nesting-conflict handling
│   └── builder.py               # drop nesting-conflict handling (keep ValueError)
├── templates/
│   ├── partials/builder.html    # category <details> in the palette; kind names on chips
│   ├── partials/icons.html      # new kinds fall back to the wrench (extra mappings where a close icon exists)
│   ├── components/form.html, detail.html, partials/storage_card.html   # show kind display names
│   └── (Jinja filter `kind_name` registered in app/main.py)
└── static/
    ├── builder.js               # drop target accepts any type except inside the dragged sub-tree
    └── styles.css               # category group styling
tests/                            # mirrors app/: models/test_component_kinds.py, services/test_component_service.py,
                                  # services/test_builder_service.py, routers/test_builder.py, routers/test_component_rules.py,
                                  # test_ui_builder_assets.py
```

**Structure Decision**: Existing layout; no new files under `app/`.

## Design Decisions (summary; detail in research.md)

1. **Catalog**: one ordered table of `(type, name, category)` for the 34 offered kinds plus a legacy list (`drivetrain`, `other`, `rim`, `spoke`, `bolt`) valid but never offered.
2. **Existing kinds reused** where the palette name matches: `frame fork wheel tire rotor brake chain saddle handlebar hub cassette crankset derailleur stem seatpost`; `pedal` → "Pedals", `shifter` → "Shift levers", `pad` → "Brake Pads" (those three move from legacy to offered; no data change).
3. **New type ids**: `accessories apparel computer lights brake_cable brake_lever bottom_bracket chainrings shifter_cable handlebar_tape headset shock axle trainer tube wheelset`.
4. **Placement**: any parent; only the cycle check remains (already implemented for moves).
5. **Palette "Add to…" targets**: every slot in scope (bike and parts), no filtering.

## Post-design Constitution re-check

Unchanged: all pass. The one-per-kind and placement rules were a feature-004/005 design choice, not a constitution rule, so no amendment is required; specs 004 and 005 are superseded for placement by this spec (noted in the spec assumptions).
