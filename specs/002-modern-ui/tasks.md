---

description: "Task list for the Modern UI feature"
---

# Tasks: Modern UI

**Input**: Design documents from `/specs/002-modern-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md (all present)

**Tests**: REQUIRED. Constitution Principle III (test-first) applies to this feature too. Because the feature is visual, tests assert what is objectively checkable (rendered markup, CSS design-token contrast, asset size, helper logic) per research.md §10; every task group lists its tests first. The existing 191 tests are the regression net and MUST keep passing unchanged (FR-014, SC-007).

**Organization**: Grouped by user story from spec.md so each story can be built and verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unmet dependency)
- **[Story]**: US1–US4 from spec.md
- Every task names its exact file path

## Path Conventions

Single project; existing `app/` and `tests/` layout. Styling is plain CSS in `app/static/styles.css` per constitution v1.3.0 (no JS framework, no build step).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared test scaffolding for the UI tests.

- [X] T001 Add a `signed_in_client` fixture to `tests/conftest.py` that stubs the Strava token exchange, completes `/auth/strava/callback`, and yields the authenticated `TestClient`, so UI tests do not each re-implement `_login`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The design-token stylesheet and icon macros that every story's markup depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Write `tests/test_ui_contrast.py` (failing first): parse the `:root` and `@media (prefers-color-scheme: dark)` token blocks from `app/static/styles.css`, compute WCAG contrast ratios, and assert per contracts/ui-contract.md §2 in BOTH themes: `--text` on `--bg` and `--surface` ≥ 4.5:1; `--text-muted` on `--surface` ≥ 4.5:1; `--primary-text` on `--primary` ≥ 4.5:1; each `--badge-*-fg` on its `--badge-*-bg` ≥ 4.5:1; focus-ring color on `--bg` ≥ 3:1. Also assert the stylesheet contains `prefers-color-scheme: dark`, `prefers-reduced-motion: reduce`, `:focus-visible`, and `color-scheme: light dark`, that the spacing, radius, shadow and type-scale tokens exist (FR-002), that a `--tap-min` token of at least 2.75rem exists and `.btn` and the primary nav links use it as `min-height` (FR-004), that long text wraps via `overflow-wrap: anywhere` and flex/grid children set `min-width: 0` (long-name edge case), and that `styles.css` is ≤ 40 KB and `styles.css` + `htmx.min.js` ≤ 150 KB (SC-001)
- [X] T003 [P] Write `tests/test_ui_icons.py` (failing first): render each macro in `app/templates/partials/icons.html` (warning, clock, check, question, chevron, plus, trash, bike, wrench, settings, sign-out) and assert each emits an `<svg>` with `aria-hidden="true"` and `focusable="false"`
- [X] T004 Rewrite `app/static/styles.css`: design tokens named per contracts/ui-contract.md §2 (light on `:root`, dark overrides in `@media (prefers-color-scheme: dark)`, `color-scheme: light dark`), system font stack, type scale, spacing/radius/shadow tokens, base reset, `.container`, `.skip-link`, `.app-header`/nav styles, `.btn` family, `:focus-visible` ring, `prefers-reduced-motion` rule, `--tap-min`, and `overflow-wrap: anywhere`/`min-width: 0` rules for long names — makes T002 pass (component, form, table, badge and tree styles are added in later phases)
- [X] T005 [P] Create `app/templates/partials/icons.html` with the inline SVG macros listed in T003 (stroke `currentColor`, `aria-hidden="true"`, `focusable="false"`) — makes T003 pass

**Checkpoint**: Tokens and icons exist; user stories can begin.

---

## Phase 3: User Story 1 - Consistent, Navigable App Shell (Priority: P1) 🎯 MVP

**Goal**: Every page shares the same frame, theme and responsive behavior.

**Independent Test**: Visit sign-in, garage, due dashboard and settings; each shows the same header with the current section highlighted and a working sign-out; works at 360 px and in both themes.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [X] T006 [P] [US1] Write `tests/test_ui_shell.py` (failing first) asserting for `/`, `/components`, `/maintenance/due`, `/settings`, `/bikes/new`: a skip link to `#main`, one `<header>` containing `<nav aria-label="Primary">` with links to `/`, `/maintenance/due`, `/settings`, a sign-out `<form method="post" action="/logout">`, a `<main id="main">`, exactly one `<h1>`, and `<meta name="viewport" content="width=device-width, initial-scale=1">`
- [X] T007 [P] [US1] In `tests/test_ui_shell.py` add: `aria-current="page"` appears on Garage for `/`, `/bikes/new` and `/components`; on Maintenance due for `/maintenance/due`; on Settings for `/settings`; and on exactly one nav link per page (contracts/ui-contract.md §1, research.md §9)
- [X] T008 [P] [US1] In `tests/test_ui_shell.py` add: the unauthenticated `/login` page renders the same `<header>` with the brand but no Garage / Maintenance due / Settings links and no sign-out form, and still has one `<h1>` and the "Sign in with Strava" link

### Implementation for User Story 1

- [X] T009 [US1] Rewrite `app/templates/layout.html` as the app shell per contracts/ui-contract.md §1: skip link, `<header class="app-header">` with `<nav aria-label="Primary">` (brand, Garage, Maintenance due, Settings, sign-out form button), `aria-current` computed from `request.url.path` (Garage: `/`, `/bikes*`, `/components*`; Maintenance due: `/maintenance/due`, `/schedules*`; Settings: `/settings*`), viewport meta, `<main id="main" class="container">`, `defer` on the HTMX script, and overridable `header`/`content` blocks — makes T006/T007 pass
- [X] T010 [US1] Restyle `app/templates/login.html` as a centered sign-in card that overrides the header block with the brand only and keeps the `strava_authorize_url` link as a primary button — makes T008 pass
- [X] T011 [US1] Add responsive shell rules to `app/static/styles.css`: nav that wraps or condenses cleanly at 360 px with tap targets ≥ 44 px, comfortable content gutters, no horizontal page scroll (FR-004)

**Checkpoint**: User Story 1 is complete and demonstrable on its own.

---

## Phase 4: User Story 2 - Garage and Component Views That Are Easy to Scan (Priority: P2)

**Goal**: Bike cards, a collapsible nested tree, empty states and a clear destructive confirmation.

**Independent Test**: With several bikes and a three-level tree, the garage and bike pages show cards and a readable, collapsible tree; empty garage/storage show guidance; deleting shows a destructive confirmation.

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [X] T012 [P] [US2] Write `tests/test_ui_pages.py` (failing first) for the garage: each bike renders as an element with class `card` containing its name link, type, total mileage, and the quick-action links View (`/bikes/{id}`), Add component (`/components/new?parent_bike_id={id}`) and Maintenance history (`/bikes/{id}/maintenance`); storage components appear under a labeled "In storage" heading; an empty database shows `.empty-state` blocks for no bikes and for empty storage, each with a primary action link (`/bikes/new`, `/components/new`)
- [X] T013 [P] [US2] In `tests/test_ui_pages.py` add for a bike with wheel → rim → tire: the tree renders nested `<details open>` / `<summary>` elements inside `.tree` (leaf nodes as plain list items), each node shows its component type and mileage, and an empty bike shows an `.empty-state`
- [X] T014 [P] [US2] In `tests/test_ui_pages.py` add: `POST /bikes/{id}/delete` and `POST /components/{id}/delete` without `confirmed` (bike with components) return, WITHOUT `hx-request`, a full page (contains `<main`, the nav, and a `.confirm` block naming the item) and, WITH `hx-request: true`, only the `.confirm` fragment (no `<html`); both contain a cancel link and a `btn-danger` confirm button; the existing confirmed-delete behavior is unchanged

### Implementation for User Story 2

- [X] T015 [US2] Add card, card-grid, `.empty-state`, `.tree` (indent connector lines, `<summary>` chevron rotating via CSS, no animation under reduced motion) and `.confirm` styles to `app/static/styles.css`
- [X] T016 [P] [US2] Restyle `app/templates/bikes/list.html` and `app/templates/partials/bike_row.html` (card with name link, type, mileage, and the quick actions View, Add component and Maintenance history) plus the "In storage" section and empty states — makes T012 pass
- [X] T017 [P] [US2] Restyle `app/templates/partials/component_tree.html` macro to emit `<details open><summary>` for nodes with children and plain list items for leaves, each showing type and mileage — makes T013 pass
- [X] T018 [P] [US2] Restyle `app/templates/bikes/detail.html`, `app/templates/components/detail.html` (header with actions, tree section, empty state, move section styled as a secondary panel) and `app/templates/components/list.html` (card list + empty state)
- [X] T019 [US2] Create `app/templates/confirm_delete_page.html` (extends `layout.html`, includes `partials/confirm_delete.html`) and restyle `app/templates/partials/confirm_delete.html` as the `.confirm` block (states what is deleted, `btn-danger` confirm, cancel link back)
- [X] T020 [US2] In `app/routers/bikes.py` and `app/routers/components.py`, render `confirm_delete_page.html` for non-HTMX unconfirmed deletes and keep returning the `partials/confirm_delete.html` fragment when `hx-request` is `true`; add `hx-post`/`hx-target`/`hx-swap` to the Delete forms in the detail templates so the confirmation appears inline — makes T014 pass

**Checkpoint**: User Stories 1 and 2 work independently.

---

## Phase 5: User Story 3 - A Maintenance Dashboard You Can Read at a Glance (Priority: P3)

**Goal**: Status badges, in-place "Mark done", dismissible alerts, a table that stacks on phones.

**Independent Test**: Schedules in each state show the right badge (text + icon + color); marking done updates one row in place; alerts dismiss in place; no schedules shows an empty state; 360 px shows stacked rows.

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [X] T021 [P] [US3] Write `tests/services/test_schedule_status.py` (failing first) for `schedule_service.due_status(projection, lead_time_days, today)` with these rules verbatim from data-model.md: `overdue` when `projection.is_overdue`; `due_soon` when not overdue, `due_at` is set, and `0 <= (due_at - today).days <= lead_time_days`; `on_track` when `due_at` is set and further out than the lead-time window; `no_estimate` when `due_at` is `None`; include boundary cases (exactly `lead_time_days` out, due today, one day past the window)
- [X] T022 [P] [US3] In `tests/test_ui_pages.py` add dashboard tests: for schedules in each state the row contains the badge text "Overdue", "Due soon", "On track" or "No estimate yet" (class `badge-overdue|badge-soon|badge-ok|badge-low`, each with an `<svg aria-hidden="true">`), a separate "Low confidence" badge when `is_low_confidence`, the table has `<th scope="col">` headers, and each `<td>` carries a `data-label`
- [X] T023 [P] [US3] In `tests/test_ui_pages.py` add: unacknowledged notifications render as `.alert` list items each with a dismiss form carrying `hx-post`, `hx-target` and `hx-swap="outerHTML"`; `POST /notifications/{id}/acknowledge` with `hx-request: true` returns 200 with an empty body and acknowledges the notification, and without it still 303-redirects to `/maintenance/due` (contracts/ui-contract.md §5); `POST /schedules/{id}/complete` with `hx-request: true` returns the `<tr id="schedule-row-{id}">` fragment containing a status badge; an empty dashboard shows an `.empty-state`

### Implementation for User Story 3

- [X] T024 [US3] Implement `due_status(projection, lead_time_days, today)` in `app/services/schedule_service.py` per the rules in T021 — makes T021 pass
- [X] T025 [US3] In `app/routers/schedules.py` pass `lead_time_days` (the account's `notification_lead_time_days`) and `today` into the dashboard and complete-row render contexts, and make `acknowledge_notification` return an empty 200 `HTMLResponse` when `hx-request` is `true` (303 redirect otherwise) — makes T023's route assertions pass
- [X] T026 [P] [US3] Create `app/templates/partials/badges.html` with a `status_badge(status)` macro and a `low_confidence_badge()` macro mapping per contracts/ui-contract.md §4 (text + icon + class); ensure the static class names `badge-overdue`, `badge-soon`, `badge-ok`, `badge-low` appear in `app/static/styles.css` token-based rules
- [X] T027 [US3] Restyle `app/templates/partials/due_soon_row.html` (status badge computed via `due_status`, `data-label` on each `<td>`, "Mark done" as `btn-primary` with the existing `hx-post`/`hx-target`/`hx-swap`, Edit and Delete as quiet/danger actions) and `app/templates/schedules/due_dashboard.html` (alerts section with dismiss forms using `hx-post`/`hx-target="closest li"`/`hx-swap="outerHTML"`, `.table-responsive` table with `<th scope="col">`, `.empty-state`) — makes T022/T023 pass
- [X] T028 [US3] Add badge, `.alert`, and `.table-responsive` styles to `app/static/styles.css`, including the below-40-rem rule that stacks rows into cards using `data-label` (no horizontal page scroll); re-run `tests/test_ui_contrast.py` to confirm badge contrast still passes

**Checkpoint**: User Stories 1–3 work independently.

---

## Phase 6: User Story 4 - Polished Forms and Feedback (Priority: P4)

**Goal**: Tidy forms with per-field errors, preserved entries, and clear action hierarchy.

**Independent Test**: Submitting invalid input to each form re-shows it with the entries preserved, the error beside the field plus a summary, visible focus, and distinct primary/secondary/destructive buttons.

### Tests for User Story 4 ⚠️ (write first, confirm they fail)

- [X] T029 [P] [US4] Write `tests/models/test_form_errors.py` (failing first) for `app/models/form_errors.py::field_errors(exc)`: maps a Pydantic `ValidationError` to `{field_name: first_message}`, ignores model-level errors with an empty location (they stay in the summary), and keeps only the first message per field
- [X] T030 [P] [US4] In `tests/test_ui_pages.py` add form tests for bike, component, maintenance, schedule, mileage-adjust and settings (webhook, lead time) forms: posting invalid data returns 422 and the page keeps the submitted values in the inputs, shows the message in an element with class `field-error` linked by `aria-describedby` with `aria-invalid="true"` on that control, and shows an `.error-summary` with `role="alert"`; every `<input>`/`<select>` has a matching `<label for>`/`id` pair
- [X] T031 [P] [US4] In `tests/test_ui_pages.py` add: each form has exactly one `btn-primary` submit; delete buttons use `btn-danger`; existing 422 status codes and error text from feature 001 are unchanged (assert a known message such as the schedule "Set a mileage interval, a time interval, or both." still appears)

### Implementation for User Story 4

- [X] T032 [US4] Implement `app/models/form_errors.py` with `field_errors(exc: ValidationError) -> dict[str, str]` per T029 — makes T029 pass
- [X] T033 [P] [US4] Create `app/templates/partials/forms.html` with macros `field(name, label, type, values, field_errors, hint, **attrs)` (label, control, hint, error with generated ids, `aria-invalid`, `aria-describedby`), `select_field(...)`, `error_summary(errors)` (`role="alert"`), and `submit(label, danger=False)` (`btn-primary` or `btn-danger`)
- [X] T034 [US4] In `app/routers/bikes.py`, `app/routers/components.py`, `app/routers/maintenance.py`, `app/routers/schedules.py`, `app/routers/mileage.py` and `app/routers/settings.py`, pass `field_errors` (from `form_errors.field_errors`) and `values` (the submitted form as a dict) in every validation-failure render alongside the existing `errors` list; do not change status codes, messages or validation
- [X] T035 [P] [US4] Restyle `app/templates/bikes/form.html`, `app/templates/components/form.html` and `app/templates/bikes/strava_pairing.html` using the `partials/forms.html` macros and `values` — makes T030/T031 pass for those forms
- [X] T036 [P] [US4] Restyle `app/templates/maintenance/form.html`, `app/templates/schedules/form.html` and `app/templates/mileage_adjust_form.html` using the `partials/forms.html` macros and `values`
- [X] T037 [P] [US4] Restyle `app/templates/settings/index.html` (separate cards for Strava connection, webhook, lead time; stale state shown with a warning badge; forms use the macros) and the move form in `app/templates/components/detail.html`
- [X] T038 [US4] Add `.field`, `.field-error`, `.field-hint`, `.error-summary`, input/select/textarea (including dark theme and focus states), and button-group styles to `app/static/styles.css`; re-run `tests/test_ui_contrast.py`

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T039 [P] Restyle `app/templates/maintenance/history_list.html` (responsive table with `<th scope="col">`, empty state, Edit/Delete actions) and `app/templates/partials/stale_connection_banner.html` (warning banner) using the existing classes
- [X] T040 [P] Add a rendered-markup test in `tests/test_ui_pages.py` that every page in the app (including `history_list` empty and populated) has a `<title>`, one `<h1>`, a `<main>`, and no inline `style=` attributes or inline `<script>` tags (earlier template tasks MUST NOT introduce inline `style=`, so this guard stays green; it also removes the leftover `style="display:inline"` uses from templates and keeps CSP-friendly markup)
- [X] T041 Run the whole suite (`.venv/bin/python -m pytest -q`) and confirm the 191 existing tests pass unchanged alongside the new UI tests
- [X] T042 Walk through `specs/002-modern-ui/quickstart.md` in the browser pane against a seeded database at 360 px and 1280 px, in light and dark (`resize_window` with `colorScheme`), with JavaScript disabled for the no-JS flow; inject axe-core (dev-time, from a pinned jsDelivr URL, in the browser pane only; never added to the app) and confirm no critical or serious violations on the garage, bike detail, dashboard, a form and settings pages in both themes; fix any visual or behavioral discrepancies found and record what was checked in the PR description
- [X] T043 [P] Update `README.md` with a short "UI and styling" note (hand-written CSS in `app/static/styles.css`, tokens, how to adjust the theme) and update the Project state / Architecture notes in `CLAUDE.md` accordingly

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **US1 (shell)** must come first: every later story's templates extend the new `layout.html`.
- **US2, US3, US4** are independent in what they deliver, but sequenced P2 → P3 → P4 because they share `app/static/styles.css`, and US3/US4 both edit `app/routers/schedules.py` and `app/templates/schedules/form.html`, US2/US4 both edit `app/templates/components/detail.html`.
- **Polish** depends on all stories.

### Parallel Opportunities

- T002 and T003 (different test files); T005 alongside T004.
- Within each story, all `[P]` test tasks together, and `[P]` template tasks touching different files together (T016–T018, T035–T037).

## Implementation Strategy

1. Setup + Foundational → tokens and icons.
2. **MVP = User Story 1**: the shell transforms every page's first impression; validate with quickstart Scenario 1.
3. Add US2 → US3 → US4, validating each against its quickstart scenario.
4. Polish, then a full-suite run and the visual walkthrough (T041–T042).

## Notes

- Constitution Principle III: confirm each test fails before its implementation task.
- Commit after each task or logical group (atomic, imperative commits).
- Do not change routes, form fields, stored data or calculations (FR-014); context additions and HTMX-aware responses are the only server-side changes.
