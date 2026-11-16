# Implementation Plan: Time Zone Labels Follow the Season

**Branch**: `074-zone-label-season` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

## Summary

Settings → Time zone entries are built by `clock_service.timezone_choices`. Today `_label` reads each zone at a fixed January/July moment chosen to be standard time (`_standard_time`), and the list is sorted by that standard offset. The change is to read each zone at one moment, the time the page is shown (UTC now), for both the label and the sort. The router and template are unchanged: the router already passes the choices and derives "Currently …" from the selected entry.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Jinja2, standard-library `zoneinfo` with the `tzdata` package (already a dependency)
**Storage**: none touched
**Testing**: pytest. Tests pass a fixed moment (`at=`) to the service, and route tests replace `clock_service._utc_now`, so results don't depend on the day CI runs.
**Target Platform**: self-hosted Linux container
**Project Type**: web service (server-rendered)
**Performance Goals**: building 33 labels per Settings render is negligible
**Constraints**: none beyond the constitution
**Scale/Scope**: one service function, its tests and one router test file

## Constitution Check

- **Fixed stack and layout**: logic stays in `app/services/clock_service.py`, with no router or template change. PASS
- **TDD**: tests change first (new seasonal cases, pinned dates in route tests), and are run failing before the code changes. PASS
- **Security, observability, data**: no input, logging or storage change. PASS

Re-checked after design: PASS. Nothing to track under Complexity.

## Project Structure

### Documentation (this feature)

```text
specs/074-zone-label-season/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

Amended outside this folder: `specs/023-settings-sync-and-timezone/spec.md` (FR-006, US2 scenario 1, Amendments) and `specs/023-settings-sync-and-timezone/contracts/routes.md` (Time zone section).

### Source Code

```text
app/services/clock_service.py      # timezone_choices(current, at=None), _label(name, at), offset_minutes(name, at), _utc_now()
tests/services/test_clock_service.py
tests/routers/test_settings.py     # pin the moment in the label tests
```

**Structure Decision**: keep everything in the existing service. `_standard_time` and `standard_offset_minutes` are removed because nothing else uses them.
