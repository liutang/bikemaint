# Implementation Plan: Unified Bike Screen and Simpler Parts

**Branch**: `005-unified-bike-screen` (built on `004-bike-builder`) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

## Summary

Two milestones:
- **M1**: replace the bike catalog with Year/Make/Model text + Category select (migration `0007`: add `year`, `make`, `model`, drop `catalog_id`; remove `bike_catalog`); simplify the offered part kinds (`component_kinds`: `offered` flag, legacy kinds hidden but valid).
- **M2**: one unified screen. The builder view is generalized from "a bike" to a **root** (`bike:ID` or `component:ID`); `GET /bikes/{id}` and `GET /components/{id}` render it with breadcrumbs, scope-specific action buttons, tree, storage and palette; builder endpoints become scope-based (`POST /builder/add|move|delete`, field `root`); per-row Garage and Trash buttons; old build route redirects; Build/Add component buttons and the separate Move form are removed.

## Technical Context

Python 3.13, FastAPI, Jinja2, HTMX, vanilla `builder.js` (already allowed by research 004 §1); SQLite migration `0007_bike_year_make_model.sql`; pytest (626 baseline). No new dependencies. Constitution v1.3.0 unchanged: PASS (no new framework, validation at the boundary, logic in services, TDD).

## Constitution Check

I Simplicity PASS (one screen instead of two; fewer kinds). II Modularity PASS (`builder_service` owns scope logic; routers parse and render). III TDD PASS. IV Security PASS (allow-listed categories and kinds, ints validated, scope checks on every request, parameterized SQL). V Observability PASS. Styling/stack PASS.

## Structure

```text
app/
├── db/migrations/0007_bike_year_make_model.sql
├── models/{component_kinds.py, requests.py, rows.py}
├── services/{bike_service.py, builder_service.py, component_service.py}   # bike_catalog.py removed
├── routers/{bikes.py, components.py, builder.py}
├── static/{builder.js, styles.css}
└── templates/{bikes/form.html, bikes/detail.html (unified), components/detail.html (unified),
              partials/{builder.html, breadcrumb.html, part_actions.html}}  # bikes/build.html removed
tests/ (mirrors app/)
```

## Complexity Tracking

None.
