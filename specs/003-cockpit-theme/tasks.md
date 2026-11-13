---

description: "Task list for the Cockpit Theme feature"
---

# Tasks: Cockpit Theme

**Input**: Design documents from `/specs/003-cockpit-theme/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md (all present)

**Tests**: REQUIRED (constitution Principle III). Write each test first and watch it fail before the code that satisfies it. Old-markup assertions may change only where this restyle intentionally replaces the markup (FR-019).

**Organization**: Grouped by user story from spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no unmet dependency)
- **[Story]**: US1–US3 from spec.md
- Every task names its exact file path

## Path Conventions

Single project; existing `app/` and `tests/` layout. Plain CSS in `app/static/styles.css` per constitution v1.3.0.

---

## Phase 1: Setup

- [X] T001 Create branch `003-cockpit-theme` stacked on `002-modern-ui` and vendor Space Grotesk and Inter variable latin-subset `.woff2` files (SIL OFL) into `app/static/fonts/` with a short `app/static/fonts/README.md` noting source and license

---

## Phase 2: Foundational (blocking)

**Purpose**: The Cockpit design tokens every story depends on.

- [X] T002 Update `tests/test_ui_contrast.py` first: new token names (`--accent`, `--accent-text`, `--accent-ink`, `--status-*-{fg,bg}`), text pairs for both themes at 4.5:1, accent text on accent fill, focus ring at 3:1, `@font-face` present for both fonts with local `url(`, no `http` URLs in the stylesheet, asset budget CSS + fonts under 250 KB (confirm it fails)
- [X] T003 Replace the token blocks in `app/static/styles.css` with the Cockpit palette (charcoal dark `#1b1e25`/`#262a33`/`#363c48`, cool-grey light `#f2f4f8`/white, accent `#FFA800`, darker amber `--accent-ink` for light-mode text uses, distinct gold due-soon), add `@font-face` rules and `--font-display`/`--font-sans`, and point existing components at the new tokens so every page already renders in the new theme

**Checkpoint**: tokens land; existing tests still pass.

---

## Phase 3: User Story 1 - Cockpit Look and Shell on Every Page (P1)

**Goal**: Pill-navigation top bar with logo, current-page accent pill, sync indicator, sign out.

**Independent Test**: Load any page; verify shell markup and "Synced …" text; sign-in page has no nav.

### Tests (first)

- [X] T004 [P] [US1] Add `tests/db/test_mileage_latest_synced.py` for `app/db/mileage.py::latest_synced_at` (None when no rides, max `synced_at` otherwise)
- [X] T005 [P] [US1] Add `tests/services/test_sync_status_service.py` for `last_sync_label(now)` ("Not synced yet", "Synced just now", "N min ago", "N h ago", "N d ago")
- [X] T006 [US1] Update `tests/test_ui_shell.py`: header contains `.sync-status`, nav pills keep `aria-current="page"` on the current section, the sign-in page shows no nav or sync status, no external font/style URLs in any page

### Implementation

- [X] T007 [P] [US1] Add `latest_synced_at(conn)` to `app/db/mileage.py` (parameterized query)
- [X] T008 [US1] Add `app/services/sync_status_service.py` with `last_sync_label` (depends on T007)
- [X] T009 [US1] Register `last_sync_label` as a Jinja global in `app/main.py` (templates setup) and render the indicator in `app/templates/layout.html`; restyle `.app-header`, pill nav, brand, sync indicator and sign-out in `app/static/styles.css`; preload the two font files in the layout head

**Checkpoint**: US1 complete and demonstrable.

---

## Phase 4: User Story 2 - "What Needs Attention" Page (P2)

**Goal**: Ring cards, six-tile cap with "+N more tasks", compact list, in-place Mark done, empty states.

**Independent Test**: Seed schedules in every state; open `/maintenance/due`, `?all=1`, mark one done via HTMX.

### Tests (first)

- [X] T010 [P] [US2] Add `tests/services/test_attention.py` covering `days_until`, `ring_fraction` (overdue 1.0, floor 0.08, clamped), `split_attention` ordering (overdue most-late first, then due-soon soonest first), cap (6 → 6 cards no overflow, 7 → 5 + 2), `show_all`, and that no-estimate/on-track items are never urgent
- [X] T011 [P] [US2] Add `tests/test_ui_attention.py`: page title "What needs attention", ring `role="img"` with aria-label text ("Overdue by 30 days", "Due in 4 days"), visible "30d"/"late" and "4d"/"left", "+2 more tasks" tile and `?all=1` link at 7 urgent, `?all=1` shows all, 2-3 urgent use `cols-2`, 4+ use `cols-3`, other tasks in the compact list with badges, all-clear and no-schedules empty states, an overdue-by-mileage item with no date shows "Late"
- [X] T012 [US2] Update HTMX tests in `tests/test_ui_pages.py` (the single-`<tr>` assertions) to expect the re-rendered `#attention` board from `POST /schedules/{id}/complete`, a hidden `all` field preserved, and the non-HTMX redirect unchanged

### Implementation

- [X] T013 [US2] Add `days_until` to `DueItem`, plus pure helpers `ring_fraction` and `split_attention` in `app/services/schedule_service.py`
- [X] T014 [P] [US2] Add ring, `arrow_right`/needed icons to `app/templates/partials/icons.html` and the `ring` macro in new `app/templates/partials/ring.html`
- [X] T015 [US2] Create `app/templates/partials/attention_board.html`, `attention_card.html` and `other_row.html`; rewrite `app/templates/schedules/due_dashboard.html` as "What needs attention" (alerts stay above; remove `due_soon_row.html` once unused)
- [X] T016 [US2] Update `app/routers/schedules.py`: parse the boolean `all` query flag with a validated model, call `split_attention`, pass board context; HTMX complete returns the board partial
- [X] T017 [US2] Add attention-grid, card, ring, overflow tile, other-list and all-clear styles to `app/static/styles.css` (2/3/1 column rules, 44 px targets, reduced-motion safe)

**Checkpoint**: US2 complete.

---

## Phase 5: User Story 3 - Every Other Screen Matches (P3)

**Goal**: Garage, tree, component pages, history, forms, settings, login, confirmations adopt the Cockpit look.

**Independent Test**: Visit each page in both themes; existing structural guards still pass.

### Tests (first)

- [X] T018 [P] [US3] Extend `tests/test_ui_contrast.py` with a status-badge token check (overdue/soon/ok/low in both themes, gold visibly distinct from `--accent` by hue) and a check that every `badge-*` rule uses status tokens

### Implementation

- [X] T019 [US3] Restyle cards, garage grid, component tree, tables, forms, alerts, banners, confirmations, sign-in and empty states in `app/static/styles.css` to the Cockpit surfaces, radii, shadows and type; keep all markup contracts (details/summary tree, `data-label` stacking, per-field errors)
- [X] T020 [US3] Update `app/templates/partials/badges.html` and `app/templates/login.html` (and any template still using removed class names) to the new tokens and classes

**Checkpoint**: all stories complete.

---

## Phase 6: Polish and Cross-Cutting

- [X] T021 Run the full suite (`.venv/bin/python -m pytest -q`); fix regressions without weakening behavioral assertions
- [X] T022 Rebuild the Docker image, seed demo data (including a 7-urgent scenario), and visually verify dark, light and 375 px in the built-in browser (screenshots)
- [X] T023 Update `README.md` "UI and styling" section and the UI note in `CLAUDE.md` (Cockpit tokens, fonts, attention board, `?all=1`); mark all tasks `[X]`

---

## Phase 7: Review follow-ups (alerts removal, theme setting, garage restyle)

- [X] T024 [US2] Tests first in `tests/test_ui_pages.py` and `tests/test_ui_attention.py`: the due page renders no "Due-soon alerts" section; remove the alert-dismissal UI tests (acknowledge route and notification recording stay and keep their service tests)
- [X] T025 [US2] Remove the alerts block from `app/templates/schedules/due_dashboard.html` and the `alerts` context from `app/routers/schedules.py`; drop unused `.alert` CSS
- [X] T026 [US4] Tests first: `tests/models/test_requests.py` (ThemeSettingsRequest accepts only system/light/dark), `tests/test_ui_theme.py` (Settings Appearance form, POST `/settings/theme` sets the cookie and redirects, invalid value is 422 and keeps the old choice, `<html data-theme>` rendered on every page incl. sign-in, absent for System), update `tests/test_ui_contrast.py` to read the dark tokens from the `data-theme="dark"` rule
- [X] T027 [US4] Add `ThemeSettingsRequest` to `app/models/requests.py`, a theme cookie helper in `app/services/theme_service.py`, `POST /settings/theme` in `app/routers/settings.py`, Appearance panel in `app/templates/settings/index.html`, and `data-theme` on `<html>` in `app/templates/layout.html`
- [X] T028 [US4] CSS: dark tokens apply for `:root[data-theme="dark"]` and, under `prefers-color-scheme: dark`, for `:root:not([data-theme="light"])`; set `color-scheme` per choice; style the radio group
- [X] T029 [US3] Tests first in `tests/test_ui_pages.py` for the garage markup (bike cards: `.bike-card` with `.bike-card-stat` mileage, primary View, quieter secondary actions; storage cards likewise); then restyle `app/templates/bikes/list.html`, `partials/bike_row.html` and the garage CSS
- [X] T030 Run the full suite, rebuild the Docker image, verify dark/light/forced-theme and the garage visually, update `contracts/ui-contract.md`, mark tasks `[X]`, commit

---

## Dependencies and Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish (US2/US3 CSS edits share one file, so run them sequentially).
- Within a story: tests first, then implementation.
- T007 → T008 → T009; T013 → T015 → T016.

## Parallel Opportunities

- T004 ∥ T005; T010 ∥ T011; T014 ∥ T013 (different files).

## Implementation Strategy

MVP = Phases 1–3 (theme + shell). Then the attention page (largest behavior change), then the remaining screens. Commit per phase.

## Amendment from user testing (branch 026-last-sync-time)

- [ ] T101 Tests first (`tests/db/test_accounts.py`, `tests/services/test_sync_service.py`, `tests/services/test_sync_status_service.py`, `tests/routers/test_mileage.py`): a successful sync run records the time even with no rides, failed and stale-skipped runs do not, backfill records it, the label prefers it and falls back to the newest ride sync. Watch fail.
- [ ] T102 Migration `0012_account_last_synced_at.sql`; `Account.strava_last_synced_at`; `accounts_db.mark_synced`; `sync_service.sync_incremental` and `backfill_bike` record it; `sync_status_service.last_sync_label` reads it. Full suite, PR, merge, confirm publish.

