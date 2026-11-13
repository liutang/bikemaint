# Implementation Plan: 028 Storage Part Links

**Branch**: `028-storage-part-links` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary

In `app/templates/partials/builder.html`, render each stored part's name in the "In storage" card as `<a href="/components/{id}">`. No route, service, data or script change: `GET /components/{id}` already renders any part, with the breadcrumb Garage › Storage › part for stored parts (`builder_service.breadcrumbs`).

## Technical Context

Python/FastAPI/Jinja2/HTMX as before; no storage or migration change; tests in `tests/routers/test_builder.py` and `tests/test_ui_builder_assets.py`.

## Constitution Check (v1.3.0)

I Simplicity: one template line. II Modular: template only. III TDD: tests first. IV Security: the link is a plain GET of an existing, sign-in-protected route. V Observability: n/a. Stack/layout: unchanged. All pass.

## Source Code

```text
app/templates/partials/builder.html   # name -> link in the In storage list
app/static/styles.css                 # only if the link needs the same text style as plain names (reuse .node-name)
tests/routers/test_builder.py         # link present on bike and part screens, breadcrumb on the target
```

## Design Decisions

- Reuse the tree's link style (`node-name`) so storage names look like the part rows beside them.
- The link text is the part's name; the kind chip stays outside the link.
- Dragging by the name keeps working (the same pattern the tree rows already use for their names).
