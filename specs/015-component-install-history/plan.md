# Implementation Plan: 015 Component Install Dates and Manual History

No new tables or libraries (constitution v1.3.0 stack unchanged). Layout:
- `app/db/components.py` — `list_periods`, `get_period`, `insert_period`, `update_period`, `delete_period`, `find_overlap`.
- `app/services/component_history_service.py` — `moment()` parsing, `list_history`, `log_period`, `update_period`, `delete_period`, validation, recompute, event logging. No FastAPI imports.
- `app/services/component_service.py` / `builder_service.py` — `installed_at` threaded through `create_component`, `mount_new_component`, `add_part`; recompute after back-dated create.
- `app/models/requests.py` — `BuilderAddRequest` gains `installed_date`/`installed_time`; new `InstallPeriodRequest`.
- `app/routers/component_history.py` — thin routes; templates `components/install_history.html`, `components/install_period_form.html`; builder partial gains date/time inputs; link from part actions.
- Tests mirror: `tests/db`, `tests/services`, `tests/routers`.

Design artifacts: [research.md](research.md), [data-model.md](data-model.md), [contracts/routes.md](contracts/routes.md) (added retrospectively).
