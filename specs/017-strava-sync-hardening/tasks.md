# Tasks: 017 Strava Sync Hardening (Retrospective)

**Input**: `specs/017-strava-sync-hardening/` (spec.md, plan.md, research.md, data-model.md, contracts/routes.md, quickstart.md)

**Tests**: Required (constitution III). Shipped tasks list the tests that already cover them; open tasks are test-first.

Format: `- [ ] ID [P] [Story] Description (file paths)`. `[x]` = shipped in PRs #12, #14, #15, #17.

## Phase 1: Shipped work (checked off, with covering tests)

### US1 — Pair a bike by gear name (P1) — PR #12 (011)

- [x] T001 [US1] Request `profile:read_all,activity:read_all` at sign-in (`app/routers/auth.py`; test `tests/routers/test_auth.py` scope assertion)
- [x] T002 [US1] Raise `StravaGearAccessError` when the athlete has no or a null `bikes` key; empty list stays valid (`app/services/strava_client.py`; tests in `tests/services/test_strava_client.py`)
- [x] T003 [US1] Show gear by name, the reconnect panel with "Sign out and reconnect", and the no-gear panel with a Strava gear settings link (`app/routers/bikes.py`, `app/templates/bikes/strava_pairing.html`; tests in `tests/routers/test_strava_pairing.py`)

### US2 — Full history on backfill (P1) — PR #14 (013)

- [x] T004 [US2] Follow activity pages until a page has fewer than 200 items, honoring `after` (`app/services/strava_client.py`; tests `test_get_activities_follows_pages_until_a_short_page`, `test_get_activities_stops_when_first_page_is_empty`)

### US3 — Re-import and unpair (P2) — PR #15 (014)

- [x] T005 [US3] `clear_strava_pairing` sets `strava_gear_id` and `strava_paired_at` to NULL (`app/db/bikes.py`)
- [x] T006 [US3] `reimport_strava_history` and `unpair_from_strava` with `NotPairedError` (`app/services/bike_service.py`; `tests/services/test_sync_service.py::test_backfill_twice_does_not_duplicate_rides`)
- [x] T007 [US3] `POST /bikes/{id}/strava-reimport` and `/strava-unpair` returning 303 / 404 / 409, plus buttons shown only when paired (`app/routers/bikes.py`, `app/templates/partials/part_actions.html`; tests in `tests/routers/test_strava_pairing.py`)

### US4 — Slow Strava responses (P2) — PR #17 (016)

- [x] T008 [US4] 60-second read timeout on activity pages (`app/services/strava_client.py`; `test_get_activities_allows_slow_strava_responses`)
- [x] T009 [US4] Re-import reports a Strava failure as 502 with a retry message (`app/routers/bikes.py`; `test_reimport_reports_a_strava_timeout_instead_of_crashing`)

## Phase 2: Remediation found by this analysis (open)

### R1 — Keep transport errors out of the router (constitution II)

- [x] T010 [US4] Write failing test: `bike_service.reimport_strava_history` raises `StravaUnavailableError` when `httpx` fails, in `tests/services/test_bike_service.py`; and `strava_client.get_activities` raises it on timeout, in `tests/services/test_strava_client.py`
- [x] T011 [US4] Add `StravaUnavailableError` to `app/services/strava_client.py`, wrapping `httpx.HTTPError` in `get_activities`, and let `bike_service` pass it through
- [x] T012 [US4] Change the router to catch `StravaUnavailableError` and remove `import httpx` from `app/routers/bikes.py`; existing `test_reimport_reports_a_strava_timeout_instead_of_crashing` must still pass (adjust its fake to the new error if it patches `httpx`)

### R2 — Log the failure paths (constitution V)

- [x] T013 [P] [US3] Write failing test with `caplog` that unpair logs an info line containing `bike_id=` in `tests/services/test_bike_service.py`; then add `logger.info("Strava pairing removed bike_id=%s", ...)` in `app/services/bike_service.py`
- [x] T014 [P] [US1] Write failing test that a missing gear list logs a warning with no token text; then log it where `StravaGearAccessError` is raised or handled (`app/services/strava_client.py` / `app/routers/bikes.py` per T011 boundary)
- [x] T015 [US4] Write failing test that a re-import timeout logs a warning with `bike_id=`; then add it in `app/services/bike_service.py`

### R3 — Docs

- [x] T016 [P] Add a "see also" note for `strava-reimport`, `strava-unpair` and the profile scope to `specs/001-bike-maintenance-tracker/contracts/routes.md`

## Phase 3: Polish

- [x] T017 Run `.venv/bin/python -m pytest -q`; all tests must pass (947 before this work)
- [x] T018 Run `/speckit-analyze` for 017; no CRITICAL or HIGH findings. MEDIUM: FR-011 (404) and FR-013 (sign-in) had no test; added in `tests/routers/test_strava_pairing.py`. MEDIUM: plan/research still listed remediation as open; updated. LOW: FR-014 (logging) added to the spec.

## Dependencies

- T010 → T011 → T012 (red, green, refactor)
- T013, T014, T016 are independent of each other (different files or tests); T014 depends on T011's boundary; T015 depends on T011.
- T017 and T018 run last.

## Implementation Strategy

Shipped stories are already complete and need no work. Do R1 first (it fixes the module boundary and defines the error the logging tasks hook into), then R2, then R3, then verify.
