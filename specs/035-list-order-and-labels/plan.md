# Implementation Plan: 035 List Order and Labels

Display order and one label only; no route, schema, contract or script change.

- **Rides**: `ride_service.get_log_for_bike` (and the part variant if shared) returns `[start, *newest_first]`; change to `[*newest_first, start]`. Running totals are computed before reversal, so values are unchanged. `rides/log.html` iterates rows in order, so no template change.
- **Part Install History**: `component_history_service.describe_history` iterates `components_db.list_periods` (oldest first). Add a newest-first ordering there (sort by `installed_at` then `id`, descending) without changing `list_periods`, which other code relies on. The bike variant already uses `list_periods_for_bike` (DESC).
- **Move control**: `app/templates/partials/builder.html` — replace the `<summary class="btn btn-quiet">Move to…</summary>` text with `ui_icons.arrow_right()` and `aria-label="Move {{ c.name }} to…"` plus a `title`. The existing visually-hidden `<label>` inside the form stays.
- **Tests first**: `tests/services/test_ride_service.py` (start last, totals unchanged), `tests/services/test_component_history_service.py` (latest first, tie by id), `tests/routers/test_builder.py` (no visible "Move to…", aria-label present, arrow icon).

Constitution v1.3.0: I Simplicity, II Modular (order in services, label in template), III TDD, IV Security (no input changes), V n/a. All pass. No research, data-model, contracts or quickstart needed: no new entities or routes.
