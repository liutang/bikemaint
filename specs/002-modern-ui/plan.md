# Implementation Plan: Modern UI

**Branch**: `002-modern-ui` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-modern-ui/spec.md`

## Summary

Restyle every page of the existing server-rendered app with one hand-written, design-token CSS file
(light and dark following the OS preference, mobile-first, no JavaScript framework and no build
step), a shared app-shell layout, and reusable Jinja macros for icons, form fields, status badges
and cards. Interactivity stays on the HTMX already vendored in the app: the nested component tree
uses native `<details>`, marking a schedule done, dismissing an alert and confirming a delete swap
in place, and forms show per-field errors while keeping the rider's entries. Behavior, routes and
stored data do not change; the small server-side additions (a status helper, a form-error helper,
and HTMX-aware responses for two existing routes) are presentation support and are test-driven.

## Technical Context

**Language/Version**: Python 3.12+ (existing); HTML (Jinja2) and CSS

**Primary Dependencies**: FastAPI, Jinja2, HTMX (existing, vendored). No new dependencies.

**Storage**: N/A — no schema or data changes

**Testing**: `pytest` with Starlette `TestClient` for rendered-markup assertions (landmarks, labels,
badges, empty states, tree markup, field errors); a unit test that computes WCAG contrast ratios
from the CSS design tokens for both themes; an asset-size budget test; the existing 191 tests
unchanged; manual visual verification in the browser pane at 360 px and 1280 px in light and dark.

**Target Platform**: Current evergreen desktop and mobile browsers (latest two majors of Chrome,
Safari, Firefox, Edge); self-hosted Linux server (unchanged)

**Project Type**: Web application — single project (unchanged)

**Performance Goals**: Fully styled first paint under 1 s on home broadband; total CSS + JS assets
per page under 150 KB (HTMX is ~51 KB, so the stylesheet budget is 40 KB with a 20 KB target)

**Constraints**: No JS framework, no runtime/deploy build step (constitution v1.3.0 Styling rule);
no new routes; no behavior change; progressive enhancement — every flow still works as plain
navigation if HTMX fails to load

**Scale/Scope**: ~20 templates, one stylesheet, ~6 small macro/partial files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Status | Notes |
|---|---|---|
| I. Simplicity Over Cleverness | PASS | One hand-written stylesheet and a few macros; native `<details>`/CSS instead of JS widgets; system font stack instead of web fonts; no CSS framework or compile step (research.md §1). |
| II. Modular, Non-Monolithic Design | PASS | Presentation lives in `app/templates/` and `app/static/`. The two server-side helpers sit in their proper layers: the status rule in `app/services/schedule_service.py`, field-error mapping in `app/models/`. Routers only pass context. |
| III. TDD (NON-NEGOTIABLE) | PASS (process gate) | `tasks.md` sequences a failing render/contrast/size test before each template or CSS change; the existing suite is the regression net (FR-014). |
| IV. Security by Default | PASS | Jinja autoescaping stays on; no inline scripts or event-handler attributes added; no external assets (no CDN, fonts or icons) so no new third-party origin; all routes keep `require_account`. |
| V. Human-Readable Observability | PASS | No logging changes. |
| Technology Stack (fixed) | PASS | Uses the new Styling rule in v1.3.0: plain, committed CSS in `app/static/`; no build step; no JS framework. |
| Project Structure (fixed) | PASS | No new top-level or `app/` directories. New files go in existing directories (`app/static/`, `app/templates/partials/`, `app/models/`). |

No violations identified; **Complexity Tracking** is empty.

*Post-Phase-1 re-check*: the design (research.md, data-model.md, contracts/) adds no dependency,
directory, route or JS. Constitution Check still PASSES.

## Project Structure

### Documentation (this feature)

```text
specs/002-modern-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── ui-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── static/
│   ├── styles.css                 # rewritten: tokens, base, shell, components, responsive
│   └── htmx.min.js                # unchanged
├── templates/
│   ├── layout.html                # app shell: skip link, header/nav, <main>, flash area
│   ├── login.html, mileage_adjust_form.html
│   ├── bikes/{list,detail,form,strava_pairing}.html
│   ├── components/{list,detail,form}.html
│   ├── maintenance/{history_list,form}.html
│   ├── schedules/{due_dashboard,form}.html
│   ├── settings/index.html
│   └── partials/
│       ├── icons.html             # new: inline SVG icon macros
│       ├── forms.html             # new: field / error-summary / button macros
│       ├── badges.html            # new: status badge macro
│       ├── bike_row.html          # restyled as a card
│       ├── component_tree.html    # restyled with <details>/<summary>
│       └── confirm_delete.html, due_soon_row.html, stale_connection_banner.html  # restyled
├── models/form_errors.py          # new: ValidationError -> {field: message}
├── services/schedule_service.py   # + due_status(): overdue / due_soon / on_track / no_estimate
└── routers/                       # context additions only (field_errors, values, lead time);
                                   # acknowledge + delete return HTMX fragments when hx-request

tests/
├── test_ui_shell.py               # shell, nav, landmarks, theme/viewport meta, asset budget
├── test_ui_pages.py               # cards, tree, empty states, dashboard badges, forms
├── test_ui_contrast.py            # WCAG contrast computed from CSS tokens (light + dark)
├── models/test_form_errors.py
└── services/test_schedule_status.py
```

**Structure Decision**: Single project, existing layout. UI tests are cross-cutting rendered-page
tests, so they sit at `tests/` top level like `tests/test_main.py` and `tests/test_quickstart.py`;
helper tests mirror their `app/` module as the constitution requires.

## Complexity Tracking

*No Constitution violations — table intentionally empty.*
