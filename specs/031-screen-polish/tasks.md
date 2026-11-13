# Tasks: 031 Screen Polish

- [ ] T001 [US1] Tests first (`tests/routers/test_schedules.py`): New schedule form Cancel href is `/bikes/{id}` or `/components/{id}`, also after a 422 error; the edit form's Cancel is `/maintenance/due`. Then `schedules.py` and `form.html`.
- [ ] T002 [US2] Tests first (`tests/services/test_component_history_service.py`, `tests/routers/test_component_history.py`): `place_url` for a parent part, a bike, a deleted parent, storage; both history pages link existing places and leave others plain. Then service and templates.
- [ ] T003 [US3] Tests first (`tests/routers/test_rides.py`): no "Edit starting mileage" on bike or part Rides, the starting row still shows its values; the Edit screens still have Baseline mileage. Then `rides/log.html`.
- [ ] T004 `CLAUDE.md` if needed; suite; PR; merge; confirm publish.
