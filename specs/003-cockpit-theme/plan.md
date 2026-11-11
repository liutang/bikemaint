# Implementation Plan: Cockpit Theme

**Branch**: `003-cockpit-theme` (stacked on `002-modern-ui`) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-cockpit-theme/spec.md`

## Summary

Re-skin the app with the approved "Cockpit" direction: replace the design tokens in `app/static/styles.css` (charcoal dark theme, cool-grey light theme, amber `#FFA800` accent, Space Grotesk + Inter vendored locally), rebuild the top bar as pill navigation with a sync indicator, and turn the Maintenance due page into "What needs attention": ring cards for urgent tasks (max six tiles, overflow collapsed into "+N more tasks"), plus a compact list for the rest. The only new logic is presentation-supporting and lives in the service layer: days late / days left, ring fill fraction, urgent/other split with the six-tile cap, and the last-sync label. No route paths, form fields, stored data or schedule calculations change; "View all" is a query option (`?all=1`) on the existing page.

## Technical Context

**Language/Version**: Python 3.13 (unchanged)
**Primary Dependencies**: FastAPI, Jinja2, HTMX (vendored), plain CSS; no new Python dependencies. Two vendored `.woff2` font files (SIL OFL) added to `app/static/fonts/`.
**Storage**: SQLite, unchanged, no migration. The sync indicator reads the existing `ride_activity.synced_at`.
**Testing**: pytest. Existing 327-test suite stays green; new tests for service helpers, ring/board rendering, nav/shell, token contrast, font self-hosting.
**Target Platform**: Self-hosted web app, current evergreen browsers; runs in Docker.
**Project Type**: Web application (server-rendered).
**Performance Goals**: Fully styled first paint without external requests; CSS + fonts under 250 KB (SC-006).
**Constraints**: Constitution v1.3.0 (plain CSS, no JS framework, no build step); routers stay free of business logic.
**Scale/Scope**: Single user; ~17 templates restyled, 1 page restructured.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity | PASS | CSS-only theming; rings are inline SVG from one macro; no JS added; "View all" is a query flag, not a new page. |
| II. Modular design | PASS | Ring math, urgent/other split and sync label go in `app/services/`; routers only pass data; templates only render. |
| III. TDD | PASS | Failing tests precede each change (service helpers, rendered board, shell, tokens). Old-markup assertions updated only where this restyle replaces them (FR-019). |
| IV. Security by default | PASS | `all` query param is validated as a boolean flag at the boundary; no new inputs stored; fonts self-hosted so no third-party requests. |
| V. Observability | PASS | No new logging needed; no secrets touched. |
| Technology Stack / Styling (v1.3.0) | PASS | Plain hand-written CSS; vendored font files are static assets like `htmx.min.js`. |

Post-design re-check: PASS (no violations; Complexity Tracking not needed).

## Project Structure

### Documentation (this feature)

```text
specs/003-cockpit-theme/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/ui-contract.md
├── checklists/requirements.md
└── tasks.md          # created by /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── routers/schedules.py          # due page: parse `all` flag, pass board data; HTMX complete returns board partial
├── services/
│   ├── schedule_service.py       # + days_until, ring_fraction, split_attention (pure helpers)
│   └── sync_status_service.py    # last-sync label (reads ride_activity via app/db)
├── db/mileage.py                 # + latest_synced_at query
├── static/
│   ├── styles.css                # new tokens + restyled components + ring/board rules
│   └── fonts/                    # SpaceGrotesk + Inter variable woff2 (vendored)
└── templates/
    ├── layout.html               # pill nav + sync indicator
    ├── schedules/due_dashboard.html      # "What needs attention"
    └── partials/
        ├── attention_board.html  # urgent cards + overflow tile + other list (HTMX swap target)
        ├── attention_card.html, other_row.html, ring.html (macro), icons.html (+ additions)
tests/                            # mirrors app/: services/, test_ui_*.py updated, + new test files
```

**Structure Decision**: Existing single-project layout; new logic in `app/services/` and `app/db/`, presentation in `app/templates/` and `app/static/`, per the constitution's Project Structure.

## Complexity Tracking

No constitution violations to justify.
