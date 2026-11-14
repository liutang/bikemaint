# Tasks: Rides for an Install Period

- [x] T001 Tests first: `tests/db/test_mileage_period_rides.py` (period filter, clock rule, deleted rides, open period), `tests/routers/test_period_rides.py` (route, 404, sign-in, no start row, total equals the period's Miles, buttons on both histories, from_bike breadcrumb, empty state).
- [x] T002 `mileage_db.list_rides_for_period` in `app/db/mileage.py`.
- [x] T003 `ride_service.get_log_for_period` and `with_start` in `app/services/ride_service.py`.
- [x] T004 Route in `app/routers/rides.py`; template changes in `app/templates/rides/log.html`.
- [x] T005 Rides buttons in `app/templates/components/install_history.html` and `app/templates/bikes/install_history.html`.
- [x] T006 Update `contracts/routes.md`, `CLAUDE.md`; full suite green.
