# Implementation Plan: 017 Strava Sync Hardening (Retrospective)

**Branch**: `017-spec-backfill` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-strava-sync-hardening/spec.md`

**Note**: Retrospective. The behavior shipped in PRs #12, #14, #15 and #17. This plan records the design as built, checks it against the constitution, and lists the gaps found (see Remediation).

## Summary

Make Strava pairing and history import dependable: request the extra Strava access that exposes the rider's gear, show gear by name with a reconnect path when access is missing, fetch every page of activities, give slow pages enough time, and let the rider re-import or unpair a paired bike without losing or duplicating rides. No new tables, libraries or migrations.

## Technical Context

**Language/Version**: Python 3 (existing `.venv`, CPython 3.13 in use)

**Primary Dependencies**: FastAPI, Jinja2, HTMX (unchanged); `httpx` for Strava calls (already a dependency); `respx` in tests

**Storage**: SQLite; reuses `bike.strava_gear_id` / `bike.strava_paired_at` and the `ride_activity` table. No migration

**Testing**: pytest, `respx` for Strava HTTP, `signed_in_client` fixture for routes

**Target Platform**: Self-hosted Linux container (existing)

**Project Type**: web-service (single FastAPI app)

**Performance Goals**: A 400+ activity history imports completely; page requests may take up to 60 s each

**Constraints**: Single user; Strava pages hold at most 200 activities; imports are idempotent by Strava activity id

**Scale/Scope**: One rider, one Strava account, hundreds to low thousands of activities

## Constitution Check

*Checked against constitution v1.3.0.*

| Principle | Result | Notes |
|---|---|---|
| I Simplicity | Pass | A plain loop for paging, one exception class for missing gear access, no new abstractions |
| II Modular design | **Partial** | See Remediation R1: `app/routers/bikes.py` imports `httpx` and catches `httpx.HTTPError`; the service layer should translate transport errors |
| III TDD | Pass (evidence by tests) | Each behavior has tests in `tests/routers/test_strava_pairing.py`, `tests/services/test_strava_client.py`, `tests/services/test_sync_service.py`. Spec-first was **not** followed; fixed by this backfill |
| IV Security | Pass | Both new POST routes depend on `require_account`; no new input; no SQL built from strings (`clear_strava_pairing` is parameterized) |
| V Observability | **Partial** | See Remediation R2: backfill logs on success, but unpair, gear-access failure and re-import timeout write no log line |
| Stack / layout | Pass | Files sit in the right directories; no new directory or dependency |

Gate result: no violation that blocks. Two partial results are tracked as remediation tasks rather than waived.

## Project Structure

### Documentation (this feature)

```text
specs/017-strava-sync-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── routes.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (as built)

```text
app/
├── routers/
│   ├── auth.py            # OAuth scope now profile:read_all,activity:read_all
│   └── bikes.py           # pairing screen (needs_profile_access), POST /bikes/{id}/strava-reimport, /strava-unpair
├── services/
│   ├── strava_client.py   # StravaGearAccessError, get_athlete_gear, paged get_activities, ACTIVITIES_TIMEOUT_SECONDS=60
│   ├── bike_service.py    # NotPairedError, reimport_strava_history, unpair_from_strava
│   └── sync_service.py    # backfill_bike (unchanged; reused by re-import)
├── db/
│   └── bikes.py           # clear_strava_pairing
└── templates/
    ├── bikes/strava_pairing.html        # gear by name, reconnect and no-gear states
    └── partials/part_actions.html       # Re-import / Unpair buttons for paired bikes

tests/                      # mirrors app/: routers/test_strava_pairing.py, routers/test_auth.py,
                            # services/test_strava_client.py, services/test_sync_service.py
```

**Structure Decision**: Existing layout; every change lives in the directory matching its responsibility.

## Remediation (gaps found by this analysis)

- **R1 (Principle II)**: Move transport-error handling out of the router. `strava_client`/`bike_service` should raise a domain error (for example `StravaUnavailableError`) and the router should map that to the 502 response, so `app/routers/bikes.py` no longer imports `httpx`.
- **R2 (Principle V)**: Add readable key=value log lines for unpair (info), missing gear access (warning) and re-import timeout (warning), each with the bike id and no secrets.
- **R3 (docs)**: Add the two new routes to a contract (`contracts/routes.md` here) and cross-reference from feature 001's route contract.

R1 and R2 change code, so they follow TDD (failing test first) in `tasks.md`.
