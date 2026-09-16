---

description: "Task list template for feature implementation"
---

# Tasks: Bike Maintenance Tracker

**Input**: Design documents from `/specs/001-bike-maintenance-tracker/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED for every task that introduces behavior. The project constitution (`.specify/memory/constitution.md`, Principle III, "NON-NEGOTIABLE") mandates test-first development for all routes, business logic, and data-access code — this is not the optional default, it is a fixed governance rule for this repo. Each user story phase below lists its tests before its implementation tasks; write them first, watch them fail, then implement.

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent implementation and testing of each story, per the source layout fixed in plan.md (`app/routers/`, `app/services/`, `app/models/`, `app/db/`, `app/templates/`, `app/static/`, `tests/` mirroring `app/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependency on another task in this list)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every task includes its exact file path

## Path Conventions

Single project per plan.md's Structure Decision — `app/` and `tests/` at the repository root (no `backend/`/`frontend/` split).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create the project skeleton directories exactly as laid out in plan.md's Project Structure: `app/routers/`, `app/services/`, `app/models/`, `app/db/migrations/`, `app/templates/{bikes,components,maintenance,schedules,settings,partials}/`, `app/static/`, `tests/{routers,services,db}/`
- [X] T002 Create `pyproject.toml` declaring the dependencies fixed in plan.md's Technical Context: `fastapi`, `uvicorn`, `jinja2`, `httpx`, `apscheduler`, `itsdangerous` (session cookie signing), and dev dependencies `pytest`, `respx`
- [X] T003 [P] Create `.env.example` documenting `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `SESSION_SECRET_KEY`, `DATABASE_PATH` per quickstart.md Prerequisites
- [X] T004 [P] Add `app/static/htmx.min.js` (vendored HTMX asset, no build pipeline per the constitution's fixed Technology Stack) and a baseline `app/static/styles.css`
- [X] T005 [P] Configure `pytest` via `[tool.pytest.ini_options]` in `pyproject.toml` (rootdir `tests/`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented — every route in every story requires an authenticated session (FR-021) against the `account`/`bike`/`component` tables.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement `app/db/connection.py`: an `sqlite3` connection helper (context-managed, `DATABASE_PATH` from env), a `schema_version` bootstrap table, and a migration runner that applies pending `app/db/migrations/*.sql` files in filename order exactly once each
- [ ] T007 Create `app/db/migrations/0001_initial.sql` creating the `account`, `bike`, `component`, and `component_installation_period` tables exactly as specified in data-model.md, including every listed column, type, and constraint (e.g. `account.strava_athlete_id INTEGER UNIQUE NOT NULL`, `account.notification_lead_time_days INTEGER NOT NULL DEFAULT 7`, `bike.strava_gear_id TEXT UNIQUE NULLABLE`, `bike.total_mileage REAL NOT NULL DEFAULT 0`, `component.component_type TEXT NOT NULL`, `component.parent_bike_id`/`component.parent_component_id` both nullable with the documented "at most one non-NULL" invariant enforced at the service layer, `component_installation_period.removed_at NULLABLE` meaning currently installed)
- [ ] T008 [P] Implement `app/models/rows.py`: typed dataclasses for `Account`, `Bike`, `Component`, `ComponentInstallationPeriod` matching the columns in T007
- [ ] T009 [P] Implement `app/services/strava_client.py` OAuth methods `exchange_code_for_token(code)` and `refresh_access_token(refresh_token)` against Strava's `/oauth/token` endpoint via `httpx`, per research.md §2
- [ ] T010 Implement `app/routers/auth.py`: `GET /login` (renders "Sign in with Strava"), `GET /auth/strava/callback` (exchanges `code`, upserts the `account` row keyed on `strava_athlete_id`, establishes the session cookie), `POST /logout` (clears session) — depends on T009
- [ ] T011 Implement an `app/services/auth_dependency.py` FastAPI dependency `require_account` that redirects to `/login` when no valid session/account exists; every protected router in later phases depends on this — depends on T006
- [ ] T012 Implement `app/main.py`: FastAPI app factory registering Starlette `SessionMiddleware` (secret from `SESSION_SECRET_KEY`), mounting `app/static/`, creating the shared `Jinja2Templates` instance, running the T006 migration runner on the `startup` event, and including the auth router — depends on T006, T010
- [ ] T013 [P] Create `app/templates/layout.html` (loads `htmx.min.js`/`styles.css`, nav shell) and `app/templates/login.html` ("Sign in with Strava" page) — depends on T004

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Maintain a Garage Inventory (Priority: P1) 🎯 MVP

**Goal**: Record bikes and arbitrarily-nested components, move components between bikes/parents/storage, with an accurate live view of the current build at every step.

**Independent Test**: Add a bike, add nested components (wheel → rim → tire), move a component to storage, reinstall it on a different bike — confirm the inventory view is correct after every step.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [ ] T014 [P] [US1] Service test for bike creation showing zero accumulated mileage (Acceptance Scenario 1), update, and soft-delete in `tests/services/test_bike_service.py`
- [ ] T015 [P] [US1] Service test for component creation that rejects a second single-instance `component_type` under an already-occupied parent while allowing the hardcoded multi-instance types (spoke, bolt, pad, other) per FR-024 and research.md §3, in `tests/services/test_component_service.py`
- [ ] T016 [P] [US1] Service test for moving a component between a bike, a different parent component, and storage, verifying `component_installation_period` rows open/close correctly and the component's own `total_mileage`/history are unchanged by the move (SC-006) in `tests/services/test_component_service.py`
- [ ] T017 [P] [US1] DB test for the recursive component-tree fetch (e.g. bike → wheel → rim → tire, arbitrary depth per FR-003) using `WITH RECURSIVE` in `tests/db/test_components.py`
- [ ] T018 [P] [US1] Router test asserting every bike/component route redirects an unauthenticated request to `/login` (FR-021) in `tests/routers/test_bikes.py` and `tests/routers/test_components.py`

### Implementation for User Story 1

- [ ] T019 [P] [US1] Implement `app/db/bikes.py` parameterized query functions: `create`, `get_by_id`, `list_active` (excludes `is_deleted`), `update`, `soft_delete`
- [ ] T020 [P] [US1] Implement `app/db/components.py` parameterized query functions: `create`, `get_by_id`, recursive tree fetch rooted at a bike or component, `update`, `move` (updates `parent_bike_id`/`parent_component_id`), recursive `soft_delete`, and `component_installation_period` open/close helpers
- [ ] T021 [P] [US1] Implement `app/models/requests.py` request schemas: `BikeCreateRequest`/`BikeUpdateRequest` (`name` required non-empty, `bike_type` optional, `manual_baseline_mileage` >= 0 default 0) and `ComponentCreateRequest`/`ComponentUpdateRequest`/`ComponentMoveRequest` (`component_type` restricted to the curated vocabulary from data-model.md, exactly one of `parent_bike_id`/`parent_component_id`/neither)
- [ ] T022 [P] [US1] Implement `app/services/bike_service.py`: `create_bike`, `update_bike`, `delete_bike` (soft-delete; requires `confirmed=true` when the bike has any installed components, per FR-020) — depends on T019, T021
- [ ] T023 [P] [US1] Implement `app/services/component_service.py`: `create_component` (enforcing the FR-024 single-instance-per-type-per-parent rule), `update_component`, `move_component` (closes the current installation period, opens a new one, or none for storage), `delete_component` (recursive soft-delete of the installed sub-tree, per FR-020/Edge Cases) — depends on T020, T021
- [ ] T024 [US1] Implement `app/routers/bikes.py`: `GET /`, `GET /bikes/{bike_id}`, `GET /bikes/new`, `POST /bikes`, `GET /bikes/{bike_id}/edit`, `POST /bikes/{bike_id}`, `POST /bikes/{bike_id}/delete` per contracts/routes.md, gated by `require_account` — depends on T011, T022
- [ ] T025 [US1] Implement `app/routers/components.py`: `GET /components`, `GET /components/new`, `POST /components`, `GET /components/{component_id}`, `GET /components/{component_id}/edit`, `POST /components/{component_id}`, `POST /components/{component_id}/move`, `POST /components/{component_id}/delete` per contracts/routes.md, gated by `require_account` — depends on T011, T023
- [ ] T026 [P] [US1] Create `app/templates/bikes/{list,detail,form}.html` and `app/templates/partials/bike_row.html`
- [ ] T027 [P] [US1] Create `app/templates/components/{list,detail,form}.html` and `app/templates/partials/{component_tree.html,confirm_delete.html}`
- [ ] T028 [US1] Wire the bikes and components routers into `app/main.py` — depends on T024, T025, T012

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Automatic Mileage Tracking from Strava (Priority: P2)

**Goal**: Pair an app bike to a Strava gear entry, periodically sync ride activity, and attribute distance to the bike and every component installed on it at ride time.

**Independent Test**: Connect Strava, pair a bike to a gear entry, record a ride in Strava, trigger a sync, confirm the ride's distance lands on the bike and its currently-installed components (including nested ones).

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [ ] T029 [P] [US2] Service test for `strava_client` activity/gear fetch and for a token-refresh failure marking `account.strava_connection_stale` (mocked via `respx`) in `tests/services/test_strava_client.py`
- [ ] T030 [P] [US2] Service test that a ride only credits mileage to components installed on the mapped bike at the ride's `occurred_at` per their `component_installation_period` (Acceptance Scenario US2-2) in `tests/services/test_sync_service.py`
- [ ] T031 [P] [US2] Service test for the one-time full-history backfill triggered on gear pairing (FR-022) in `tests/services/test_sync_service.py`
- [ ] T032 [P] [US2] Service test for a manual `mileage_adjustment` (signed `delta_miles`, optional `reason`) updating `total_mileage` and leaving an audit row (FR-009) in `tests/services/test_sync_service.py`
- [ ] T033 [P] [US2] DB test that re-syncing the same `strava_activity_id` does not create a duplicate `ride_activity` row (idempotent upsert) in `tests/db/test_mileage.py`
- [ ] T034 [P] [US2] Router test that `/bikes/{id}/strava-pairing` and `/sync/strava` require an authenticated session in `tests/routers/test_mileage.py`

### Implementation for User Story 2

- [ ] T035 [US2] Create `app/db/migrations/0002_ride_activity_and_mileage_adjustment.sql` creating the `ride_activity` and `mileage_adjustment` tables exactly as specified in data-model.md (`ride_activity.strava_activity_id UNIQUE NOT NULL`, `ride_activity.bike_id NULLABLE` for unmapped gear, `mileage_adjustment` requiring exactly one of `bike_id`/`component_id` set)
- [ ] T036 [P] [US2] Implement `app/db/mileage.py`: `ride_activity` upsert keyed on `strava_activity_id`, `mileage_adjustment` insert, and `total_mileage` recompute (baseline + attributed rides + adjustments) for a bike or component
- [ ] T037 [US2] Extend `app/services/strava_client.py` with `get_athlete_gear()` and `get_activities(after_cursor)` (paginated) — depends on T009
- [ ] T038 [US2] Implement `app/services/sync_service.py`: incremental sync from the account's last-synced cursor, the pairing backfill sync, mileage attribution walking `component_installation_period` by ride `occurred_at`, and `total_mileage` recompute for every affected bike/component — depends on T036, T037
- [ ] T039 [US2] Extend `app/services/bike_service.py` with `pair_to_strava_gear(bike_id, strava_gear_id)`, recording `strava_gear_id`/`strava_paired_at` and triggering T038's backfill — depends on T022, T038
- [ ] T040 [US2] Extend `app/services/sync_service.py` (or a sibling module) with `adjust_bike_mileage`/`adjust_component_mileage` recording a `mileage_adjustment` row (FR-009) — depends on T036
- [ ] T041 [US2] Implement `app/services/scheduler.py` registering an APScheduler interval job (default 30 min, env-configurable) that calls `sync_service`'s incremental sync — depends on T038
- [ ] T042 [US2] Register the scheduler's start/shutdown in `app/main.py`'s `startup`/`shutdown` events — depends on T041, T012
- [ ] T043 [US2] Extend `app/routers/bikes.py` with `GET`/`POST /bikes/{bike_id}/strava-pairing` — depends on T039, T024
- [ ] T044 [US2] Implement `app/routers/mileage.py`: `POST /sync/strava`, `GET`/`POST /bikes/{bike_id}/mileage/adjust`, `GET`/`POST /components/{component_id}/mileage/adjust` — depends on T040, T011
- [ ] T045 [US2] Implement `app/routers/settings.py`: `GET /settings` (connection status incl. stale flag), `POST /settings/strava/reconnect` — depends on T037, T011
- [ ] T046 [P] [US2] Create `app/templates/bikes/strava_pairing.html`, `app/templates/partials/stale_connection_banner.html`, `app/templates/mileage_adjust_form.html`, `app/templates/settings/index.html`
- [ ] T047 [US2] Wire the mileage and settings routers into `app/main.py` — depends on T044, T045, T028

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Log Completed Maintenance (Priority: P3)

**Goal**: Record completed maintenance against a bike or component and see a full, correct history for it.

**Independent Test**: Log a maintenance entry against a bike/component with a description and date; confirm it appears in that item's history with the mileage at the time.

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [ ] T048 [P] [US3] Service test for logging maintenance capturing `description`, `performed_at`, and a `mileage_at_service` snapshot (FR-010) in `tests/services/test_maintenance_service.py`
- [ ] T049 [P] [US3] Service test that a component's maintenance history stays attached to the component (not its original bike) after it moves to a different bike (Acceptance Scenario US3-2) in `tests/services/test_maintenance_service.py`
- [ ] T050 [P] [US3] Service test for editing and deleting a log entry updating the item's history (FR-012) in `tests/services/test_maintenance_service.py`
- [ ] T051 [P] [US3] DB test for chronological ordering of `maintenance_log_entry` rows in `tests/db/test_maintenance.py`

### Implementation for User Story 3

- [ ] T052 [US3] Create `app/db/migrations/0003_maintenance_log_entry.sql` creating the `maintenance_log_entry` table exactly as specified in data-model.md (`bike_id`/`component_id` nullable with exactly one set, `description NOT NULL`, `performed_at NOT NULL`, `mileage_at_service NOT NULL`, `schedule_id` nullable FK)
- [ ] T053 [P] [US3] Implement `app/db/maintenance.py`: `create`, `get_by_id`, `list_for_bike`/`list_for_component` (chronological order), `update`, `delete`
- [ ] T054 [US3] Implement `app/services/maintenance_service.py`: `log_maintenance` (defaults `mileage_at_service` to the item's current `total_mileage`), `update_entry`, `delete_entry` — depends on T053
- [ ] T055 [US3] Implement `app/routers/maintenance.py`: `GET .../maintenance`, `GET .../maintenance/new`, `POST .../maintenance`, `GET /maintenance/{entry_id}/edit`, `POST /maintenance/{entry_id}`, `POST /maintenance/{entry_id}/delete` for both bike and component owners — depends on T054, T011
- [ ] T056 [P] [US3] Create `app/templates/maintenance/{history_list,form}.html`
- [ ] T057 [US3] Wire the maintenance router into `app/main.py` — depends on T055, T047
- [ ] T058 [US3] Extend `bike_service.delete_bike`/`component_service.delete_component`'s confirmation check (FR-020) to also require confirmation when the item has maintenance history — depends on T022, T023, T054

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Schedule Maintenance and Get Notified When It's Due (Priority: P4)

**Goal**: Define maintenance schedules, project due dates from riding pace, notify the user (in-app + webhook) when something is due soon, and recalculate cleanly on completion or component moves.

**Independent Test**: Create a schedule with a mileage/time interval, observe a projected due date from riding pace, check it off, confirm the next due date recalculates from that completion.

### Tests for User Story 4 ⚠️ (write first, confirm they fail)

- [ ] T059 [P] [US4] Service test for due-date projection combining trailing riding pace (research.md §4: 90-day trailing window) with a mileage interval, a time interval, or both, taking whichever is sooner (Acceptance Scenario US4-1, spec Assumptions) in `tests/services/test_schedule_service.py`
- [ ] T060 [P] [US4] Service test for the low-confidence fallback when there is insufficient ride history (fewer than the configured minimum ride-days), falling back to time-only or flagging low-confidence (Acceptance Scenario US4-5, FR-018) in `tests/services/test_schedule_service.py`
- [ ] T061 [P] [US4] Service test that projection recalculates from the component's own mileage/pace after it moves to a different bike or into storage (Acceptance Scenario US4-4, FR-017) in `tests/services/test_schedule_service.py`
- [ ] T062 [P] [US4] Service test that completing a schedule creates a `maintenance_log_entry`, increments `cycle_number`, and resets `baseline_mileage`/`baseline_date` (FR-016) in `tests/services/test_schedule_service.py`
- [ ] T063 [P] [US4] Service test that two consecutive due-checks against the same uncompleted cycle produce exactly one `notification` row, enforced by the `UNIQUE(schedule_id, cycle_number)` constraint (FR-015) in `tests/services/test_notification_service.py`
- [ ] T064 [P] [US4] Service test for webhook delivery success/failure/retry (5s timeout, up to 2 retries) that never blocks recording the in-app notification (research.md §6) using a mocked `httpx` transport in `tests/services/test_notification_service.py`
- [ ] T065 [P] [US4] Router test that `GET /maintenance/due` lists every upcoming/overdue item across the garage in one view (FR-019, SC-005) in `tests/routers/test_schedules.py`

### Implementation for User Story 4

- [ ] T066 [US4] Create `app/db/migrations/0004_maintenance_schedule_and_notification.sql` creating the `maintenance_schedule` and `notification` tables exactly as specified in data-model.md, including `UNIQUE(schedule_id, cycle_number)` on `notification`
- [ ] T067 [P] [US4] Implement `app/db/schedules.py`: `create`, `get_by_id`, `list_active_for_bike`/`list_active_for_component`, `list_all_active` (for the due-soon dashboard), `update`, `complete` (bump `cycle_number`, reset baseline), `delete`
- [ ] T068 [P] [US4] Implement `app/db/notifications.py`: `insert` (respecting the uniqueness constraint), `list_unacknowledged`, `mark_acknowledged`, record webhook delivery result
- [ ] T069 [US4] Implement `app/services/schedule_service.py`: `project_due_date` (per research.md §4) and `complete_schedule` (creates a `maintenance_log_entry` via `maintenance_service.log_maintenance`, bumps the cycle) — depends on T067, T054
- [ ] T070 [US4] Implement `app/services/notification_service.py`: `check_due_schedules` (iterates active schedules, computes projections, inserts a `notification` row when newly within the account's `notification_lead_time_days` window) and `deliver_webhook` (per contracts/webhook-payload.md: `httpx` POST, 5s timeout, up to 2 retries, failure logged to `webhook_delivery_error` but never blocking the in-app record) — depends on T068, T069
- [ ] T071 [US4] Extend `app/services/scheduler.py` with a second APScheduler interval job (default 60 min, env-configurable) calling `notification_service.check_due_schedules` — depends on T070, T041
- [ ] T072 [US4] Implement `app/routers/schedules.py`: `GET /maintenance/due`, `GET`/`POST /bikes/{bike_id}/schedules[/new]`, `GET`/`POST /components/{component_id}/schedules[/new]`, `GET /schedules/{schedule_id}/edit`, `POST /schedules/{schedule_id}`, `POST /schedules/{schedule_id}/complete`, `POST /schedules/{schedule_id}/delete` — depends on T069, T011
- [ ] T073 [US4] Extend `app/routers/settings.py` with `POST /settings/webhook` and `POST /settings/notifications` (lead-time) — depends on T070, T045
- [ ] T074 [P] [US4] Create `app/templates/schedules/{due_dashboard,form}.html`, `app/templates/partials/due_soon_row.html`; extend `app/templates/settings/index.html` with webhook/lead-time forms
- [ ] T075 [US4] Wire the schedules router (and settings extensions) into `app/main.py` — depends on T072, T073, T057
- [ ] T076 [US4] Extend `bike_service.delete_bike`/`component_service.delete_component`'s confirmation check (FR-020) to also require confirmation when the item has an active `maintenance_schedule` — depends on T058, T069

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T077 [P] Add structured, human-readable logging (request id, resource id; Constitution Principle V) to `sync_service`, `notification_service`, and the auth flow
- [ ] T078 [P] Write `README.md` documenting setup, environment variables, and how to run the app (`uvicorn app.main:app --reload`)
- [ ] T079 Walk through quickstart.md end-to-end against the running app and fix any discrepancies found
- [ ] T080 Security review pass: confirm every route depends on `require_account` (FR-021), all `app/db/*` queries are parameterized (Constitution Principle IV), and the session cookie is `Secure`/`HttpOnly`/`SameSite`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (auth + core inventory tables gate every route).
- **User Story 1 (Phase 3)**: Depends only on Foundational.
- **User Story 2 (Phase 4)**: Depends on Foundational; extends `bike_service.py` and `strava_client.py` from Phase 2/3, so its service/router tasks are sequenced after US1's equivalents even though the story is independently testable once built.
- **User Story 3 (Phase 5)**: Depends on Foundational; its FR-020 extension task (T058) touches US1's `bike_service.py`/`component_service.py`.
- **User Story 4 (Phase 6)**: Depends on Foundational and on `maintenance_service.py` (US3) for `complete_schedule`; its FR-020 extension task (T076) builds on T058.
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### User Story Dependencies

Each story is independently testable per its "Independent Test" above once Foundational is done. US2–US4 reuse and extend files from earlier phases (noted per-task above via "depends on"), so within this single-developer task list they are sequenced P1→P2→P3→P4; a team could still parallelize by having each developer own a different service/router file per story where no shared-file edit is listed.

### Parallel Opportunities

- All Setup tasks marked `[P]` (T003–T005).
- Foundational tasks marked `[P]` (T008, T009, T013) once their own prerequisites are done.
- Within each story, all `[P]` test tasks can run together, and all `[P]` model/db/service tasks touching different files can run together, per the markers above.

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 together:
Task: "Service test for bike creation/edit/soft-delete in tests/services/test_bike_service.py"
Task: "Service test for component nesting validation in tests/services/test_component_service.py"
Task: "Service test for component move preserving mileage/history in tests/services/test_component_service.py"
Task: "DB test for recursive component tree fetch in tests/db/test_components.py"
Task: "Router test for auth-gating on bikes/components routes in tests/routers/test_bikes.py"

# Db + model + service layer for User Story 1 together:
Task: "Implement app/db/bikes.py"
Task: "Implement app/db/components.py"
Task: "Implement app/models/requests.py"
Task: "Implement app/services/bike_service.py"
Task: "Implement app/services/component_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — includes Strava-sign-in auth, which every later story also needs)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run Scenario 1 of quickstart.md
5. Demo the garage-inventory MVP

### Incremental Delivery

1. Setup + Foundational → sign-in and empty garage ready
2. Add User Story 1 → validate via quickstart.md Scenario 1 → demo
3. Add User Story 2 → validate via quickstart.md Scenario 2 → demo
4. Add User Story 3 → validate via quickstart.md Scenario 3 → demo
5. Add User Story 4 → validate via quickstart.md Scenario 4 → demo
6. Phase 7 polish, then a full quickstart.md pass (T079)

## Notes

- `[P]` tasks touch different files with no unmet dependency in this list.
- `[Story]` labels map each task to its user story for traceability; Setup/Foundational/Polish carry no label by design.
- Constitution Principle III makes the "Tests" subsection of every story mandatory here, not optional — do not skip writing/failing them first.
- Several later-story tasks (T039, T043 in US2; T058 in US3; T076 in US4) intentionally extend files created in earlier stories (`bike_service.py`, `component_service.py`) rather than duplicating logic — expect merge/edit conflicts if working these in parallel across developers.
- Commit after each task or logical group, per the constitution's Git Practices (atomic, imperative-mood commits).
