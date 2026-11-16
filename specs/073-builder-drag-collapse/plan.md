# Implementation Plan: Smoother Drag and Collapsible Parts in the Builder

**Branch**: `073-builder-drag-collapse` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

## Summary

This brings the approved prototype into the app. Three things change:

- **Drag feedback (`app/static/builder.js`)**: the dragged tree item is lifted out with an `is-lifted` class. A gap item (`li.drop-slot`) is moved to the would-be drop position. Rows and the gap glide with the Web Animations API (FLIP). Zones are measured from where rows settle and are sticky.
- **Collapsible parts (`partials/builder.html`)**: rows with sub-parts render a chevron button and an "N parts" count; rows without them render a spacer. The script toggles `is-collapsed` and stores the collapsed ids in `localStorage`.
- **Count (`builder_service.BuilderNode`)**: a new `descendant_count` property supplies N.

The server routes and request fields are unchanged.

## Technical Context

- **Language/Version**: Python 3.13; vanilla ES2020 in the one allowed static script.
- **Primary Dependencies**: FastAPI, Jinja2, HTMX 2.0.10. Nothing new.
- **Storage**: none on the server. The collapsed set lives in `localStorage` under the key `bikemaint.collapsed` (a viewer convenience).
- **Testing**: pytest, covering:
  - the rendered markup;
  - static checks of the script and CSS;
  - the drag and collapse behavior, checked in a browser against a local server (as in specs/004).
- **Target Platform**: desktop browsers with native drag and drop. Touch devices keep using the forms.
- **Constraints**:
  - `builder.js` stays at or under 16 KB (raised from 12 KB; see research §5), with no `innerHTML`, `eval` or network calls besides `htmx.ajax` (`tests/test_ui_builder_assets.py`).
  - Every class the script toggles is styled.
- **Scale/Scope**: one template, one script, CSS, and one service property.

## Constitution Check

| Principle | Status |
|---|---|
| I. Fixed stack (FastAPI + HTMX + Jinja2 + SQLite; JS only as `builder.js`) | Pass. The behavior stays in `builder.js` and the markup is server-rendered. |
| II. Layout (routers thin, services pure) | Pass. The count is a property on the service's dataclass. |
| III. TDD | Pass. Failing tests come first for the markup, the count, the script contract and the CSS. |
| IV. Security | Pass. No new input; the script sends the same validated requests. |
| V. Observability | N/A. No server logic changes. |
| VI. Git | Pass. Short-lived branch and a PR. |

## Project Structure

```text
app/services/builder_service.py     BuilderNode.descendant_count
app/templates/partials/builder.html chevron button / spacer / count per row
app/static/builder.js               gap, FLIP glide, sticky zones, collapse toggle, spring-open
app/static/styles.css               section "specs/073": slot, twisty, count, collapsed, lifted
tests/services/test_builder_service.py   count
tests/routers/test_builder.py            markup
tests/test_ui_builder_assets.py          script and CSS contract
```

## Phase 0 / Phase 1

- [research.md](research.md): FLIP versus CSS transitions, localStorage versus a server setting, and the size budget.
- [contracts/ui-contract.md](contracts/ui-contract.md): the markup and class contract.
- [quickstart.md](quickstart.md): manual browser checks.
- No data model, because nothing is stored on the server.

The post-design Constitution Check is unchanged: all pass.
