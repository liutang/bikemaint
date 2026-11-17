# Quickstart: 075 Store Typed Times in UTC

Automated: `.venv/bin/python -m pytest -q` passes.

The manual checks below use a copy of a real database with the zone set to New York.

## 1. The update converts once (US3)

1. Note down before updating:
   - each bike's and part's mileage;
   - one part's Install History (each period's Miles and Rides);
   - one bike's Maintenance history (dates, times, order);
   - one manual ride's time.
2. Start the updated app with that database.
3. Check:
   - A file `<db-stem>-before-075-<today><suffix>` exists beside the database.
   - Every value from step 1 is the same. The manual ride's time now reads `… EST` or `… EDT`.
4. Restart the app. No new copy file appears, and nothing changes.

## 2. Typing a time (US1)

1. Add a manual ride on 2026-11-16 at 5:39 PM. The Rides list shows `2026-11-16 5:39PM EST`, in the same style as the Strava rows.
2. Open Edit on a Strava ride. The time field shows the local time, matching the list.
3. Save it without changes. Its time and the bike's mileage don't change.
4. Log a period on a part with a typed install time. Install History shows it with `EST`.

## 3. Maintenance dates (US2)

1. Log maintenance on 2026-11-16 at 9:00 PM.
2. Check:
   - It reads `2026-11-16 9:00PM EST`.
   - It is listed under the 16th, below an untimed entry dated the 17th.
3. Add a schedule by months of the same service type. It counts from 2026-11-16.

## 4. Changing the zone (US4)

1. Switch Settings to Los Angeles.
2. Check:
   - The manual ride reads `2:39PM PST`.
   - The 9:00 PM entry reads `6:00PM PST`.
   - Untimed entries keep their dates.
   - Mileage totals are unchanged.
3. Switch back to New York. Every time reads as before.

## 5. Today (US5)

With the server clock on UTC, after 7 PM New York time:

- Maintenance due shows today's local date in its day counts.
- Mark done records today's local date.

## 6. Old backup (FR-009)

1. Restore a backup downloaded before this change.
2. Check that manual rides and typed install times read the same local times as they did before.
3. Download a new backup. It reads `"format": 2`.
