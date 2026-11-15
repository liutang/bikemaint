# Plan
- `backup_service`: `backup_filename(now=None)` (saved zone, `-HHMMSS`, collision suffix handled in the writer), `rolling_config()` from env, `write_rolling_backup()` (tmp file then `os.replace`, prune by sorted name over a strict regex), `list_rolling_backups()`.
- `scheduler.start()`: add `rolling_backup` job when configured.
- `routers/backup.py`: dated download name; `POST /settings/backup/run`; `routers/settings._settings_page` adds `backup` context; settings template section.
- Docs: README, `.env.example`, compose snippet. Constitution: logic in service, secrets only from environment (paths are not secret), parameter-free file ops.
