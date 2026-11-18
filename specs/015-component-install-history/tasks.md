# Tasks: 015

- [x] T001 Tests then code: db period queries (`tests/db/test_components_periods.py`)
- [x] T002 Tests then code: history service incl. saddle A/B example, overlap, validation, recompute (`tests/services/test_component_history_service.py`)
- [x] T003 Tests then code: install date on add via service and `/builder/add` (`tests/services/test_component_service.py`, `tests/routers/test_builder.py`)
- [x] T004 Tests then code: install-history routes and templates (`tests/routers/test_component_history.py`)
- [x] T005 Full suite, docs (CLAUDE.md note), PR, merge
- [x] T-051 Compare rides and periods in one clock: `app/db/frames.py` SQL functions, used by every ride/period join; startup recompute of part totals (FR-013); tests `tests/db/test_mileage_period_frames.py`.
- [x] T006 (branch `078-open-period-move`, FR-014) Failing tests, then fix: saving a still-installed period with a new Bike or Inside part moves the part there as of its install moment, with no new period; parts inside it keep their own install moments and follow it to that bike; an Inside part records the bike it is on (none in storage); moving into its own sub-tree is refused (`component_history_service._place_open_period`, `components_db.set_open_period_bike`; `tests/services/test_component_history_service.py`)
