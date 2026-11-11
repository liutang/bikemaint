# Implementation Plan: Bike Catalog and Interactive Builder

**Branch**: `004-bike-builder` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-bike-builder/spec.md`

## Summary

Three milestones, each independently shippable and image-tagged:

- **M1 Bike catalog (US1)**: a curated catalog of ~60 common bikes (`app/services/bike_catalog.py`); Add/Edit bike becomes a grouped `<select>`; name = "Make Model" with numeric suffix for duplicates; type derived. New nullable `bike.catalog_id` column.
- **M2 Compatibility rules (US2)**: one component-kind catalog (`app/services/component_catalog.py`) listing, per type, the parent kinds it may mount on; enforced in `component_service` for create, update (type change) and move; vocabulary extended; existing forms show only valid parents/types and relay a clear message.
- **M3 Builder (US3)**: `GET /bikes/{id}/build` split screen (tree left, storage list + part palette right); sibling `position` column; HTMX-swapped `#builder` fragment; a small vanilla `app/static/builder.js` for HTML5 drag and drop that posts to the same endpoints the no-JS "Move to…" forms use.

## Technical Context

**Language/Version**: Python 3.13 (unchanged)
**Primary Dependencies**: FastAPI, Jinja2, HTMX (vendored); one hand-written static script `builder.js` (no library); no new Python dependencies.
**Storage**: SQLite. Migration `0005_bike_catalog_id.sql` (bike.catalog_id TEXT NULL) in M1; `0006_component_position.sql` (component.position INTEGER NOT NULL DEFAULT 0, backfilled by id order) in M3.
**Testing**: pytest (419 passing baseline). Service-level tests for catalogs and rules; router/UI tests for forms, fragments and markup; static checks on `builder.js` (served, no external URLs, handlers present). Drag behavior itself is verified manually in the browser at the M3 checkpoint.
**Target Platform**: Self-hosted web app in Docker.
**Project Type**: Web application (server-rendered).
**Performance Goals**: Builder actions return an updated fragment in a single request.
**Constraints**: Constitution v1.3.0; routers hold no business logic; validation at the boundary; parameterized SQL.
**Scale/Scope**: Single user; ~60 catalog bikes; ~25 component kinds.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity | PASS | Catalogs are plain Python data; rules are one dict; DnD is native HTML5, no library. |
| II. Modular design | PASS | Catalog + rules in `app/services/`; routers only parse and delegate; JS only forwards drops to endpoints. |
| III. TDD | PASS | Tests precede each task; milestones end green. |
| IV. Security by default | PASS | Server re-validates every placement; catalog ids and component types are allow-listed; positions and ids validated as ints; no new secrets. |
| V. Observability | PASS | Move/mount/reorder log one readable line with ids. |
| Stack / Styling v1.3.0 | PASS with note | The stack says HTMX is the default interactivity; HTML5 drag and drop has no HTMX equivalent, so a ~150-line vanilla script is used. It is not a framework, adds no build step, is optional (all actions work through forms without it), and is recorded in research.md §1. No amendment required. |

Post-design re-check: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/004-bike-builder/
├── plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/routes.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── db/migrations/0005_bike_catalog_id.sql, 0006_component_position.sql
├── db/bikes.py, db/components.py          # catalog_id; position + ordered reads + reorder
├── models/requests.py                     # catalog-id bike requests; builder request models; vocabulary
├── services/
│   ├── bike_catalog.py                    # NEW: entries, grouping, naming
│   ├── component_catalog.py               # NEW: kinds, allowed parents, messages, valid targets
│   ├── bike_service.py, component_service.py  # use catalogs; reorder; builder view model
├── routers/bikes.py, components.py        # form handling; builder routes
├── static/builder.js, styles.css          # DnD script; builder styles
└── templates/bikes/form.html, bikes/build.html, partials/builder_*.html, component_tree.html
tests/ (mirrors app/)
```

**Structure Decision**: Existing single-project layout; reference data lives in services, presentation in templates/static.

## Complexity Tracking

No violations to justify.
