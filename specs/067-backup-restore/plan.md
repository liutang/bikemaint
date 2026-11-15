# Plan
- `app/services/backup_service.py`: schema-driven (`PRAGMA table_info`) so future columns are included; tables in dependency order; `parse_backup(raw)` validates; `restore_backup(data)` deletes in reverse order, inserts with `PRAGMA defer_foreign_keys = ON`, checks `foreign_key_check`, applies whitelisted account settings, recomputes totals. ValueError on any problem (transaction rolls back).
- `app/routers/backup.py`: the two routes; Settings page gets a section (`settings/index.html`) and a result/error message.
- Tests mirror: tests/services/test_backup_service.py, tests/routers/test_backup_routes.py.
