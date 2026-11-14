# Tasks: 038 Maintenance Mileage From Ride History

- [ ] T001 Tests first: `tests/db/test_mileage_at.py`, `tests/services/test_maintenance_service.py`, `tests/routers/test_maintenance.py` as in plan. Watch fail.
- [ ] T002 `app/db/mileage.py`: `bike_mileage_at`, `component_mileage_at`.
- [ ] T003 `maintenance_service.log_maintenance` uses them when mileage is blank.
- [ ] T004 Form hint; routes contract note; update older tests that expect the current total for past dates.
- [ ] T005 Suite; PR; merge; confirm publish.
