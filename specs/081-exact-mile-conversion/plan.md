# Implementation Plan: Exact Mile Conversion

**Branch**: `081-exact-mile-conversion` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

There are two changes:
- **The constant:** `sync_service.METERS_PER_MILE` becomes 1609.344.
- **A one-time data step,** `0022_exact_miles`, multiplies `distance_miles` by 1609.34 / 1609.344 for every `ride_activity` row with `source = 'strava' AND user_modified = 0`. It's added to `connection.DATA_STEPS` with `copy_first=False`.

Totals are recomputed by the existing startup recompute. Details are in [research.md](research.md) and [data-model.md](data-model.md).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: none new
**Storage**: SQLite. No schema change. One data step recorded in `schema_version`.
**Testing**: pytest.
- The constant is tested through a sync of 16,093.44 m giving exactly 10.0 mi.
- The step is tested on seeded rows (unedited Strava, edited Strava, manual, deleted, filtered-out) and for running once.

**Target Platform**: self-hosted Linux container
**Performance Goals**: one UPDATE over a single rider's rides. Negligible.
**Constraints**:
- all or nothing, once;
- no copy, and no backup format change (spec FR-004);
- manual and edited rides untouched (FR-003).

**Scale/Scope**: 2 app modules, 2 test files, an amendment to 001 and CLAUDE.md.

## Constitution Check

- **Fixed stack**: no change. PASS
- **Layout**:
  - The conversion constant stays in the service.
  - The data step lives in `app/db/typed_times.py`, beside the other data steps; it's a data-correction helper, not a service.
  - Tests mirror the files.

  PASS
- **I. Simplicity**: one parameterized UPDATE, using the existing `DATA_STEPS` mechanism. PASS
- **III. TDD**: failing tests first, for both changes. PASS
- **IV. Security**: no new input. The SQL is parameterized. PASS
- **V. Observability**: the step logs `data step done step=0022_exact_miles ride_activity=N`. PASS
- **Git**: one branch, one PR. PASS

## Project Structure

```text
specs/081-exact-mile-conversion/  spec.md plan.md research.md data-model.md quickstart.md tasks.md
app/services/sync_service.py      METERS_PER_MILE = 1609.344
app/db/typed_times.py             exact_miles(conn) -> {"ride_activity": n}
app/db/connection.py              DATA_STEPS += ("0022_exact_miles", typed_times.exact_miles, False)
tests/services/test_sync_service.py, tests/db/test_typed_times.py
```

## Complexity Tracking

None.
