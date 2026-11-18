# Quickstart: 076 Four-Digit Years, Two-Digit Typing

## Prerequisites

The app runs locally (see `CLAUDE.md`), signed in, with the saved zone set to New York.

## US1: two-digit years

1. **Ride:** add a manual ride, typing the date as 7/17/26, at 9:00 AM. The Rides list shows `2026-07-17 9:00AM EDT`.
2. **Install History:** Log a period with an install date typed as 3/1/25. The row reads 2025-03-01.
3. **Maintenance:** log maintenance on 1/5/26. The history shows 2026-01-05.
4. **Bike model Year:** Edit a bike and type 23. It saves as 2023. Type 99: it's refused with "Year must be between 1900 and …".
5. **Refused dates:** type the year 202 on any date: the form shows "Enter a valid date". Log a period with overlapping dates typed as two digits: the refused form shows the four-digit years.

## US1: future rides

6. Add a ride dated tomorrow: it's refused with "The ride date cannot be in the future." Add one for today with no time: it's saved.

## US2: four-digit storage

7. Run `.venv/bin/python -m pytest -q tests/db/test_frames.py`. The year-999 test passes. It fails without the fix on Linux.

## US3: repair

8. Copy a database or backup that holds `21-04-18T04:56:02.000000Z` as an install moment, then start the app (or restore the backup) with New York saved. The period starts `2021-04-18T04:00:00.000000Z`, the part's miles include every ride since then, and `schema_version` lists `0020_four_digit_years` once. A second start changes nothing.
