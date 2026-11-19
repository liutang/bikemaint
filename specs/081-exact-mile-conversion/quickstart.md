# Quickstart: 081 Exact Mile Conversion

1. **The step:** copy a database with Strava rides, start the app, and note a bike's total before and after.
   - The total drops by about 0.00025%.
   - `schema_version` lists `0022_exact_miles` once.
   - Manual and edited rides are unchanged.
   - A second start changes nothing.
2. **New rides:** sync a ride, then compare its miles with Strava's distance in meters ÷ 1,609.344.
3. **Tests:** run `.venv/bin/python -m pytest -q`.
