# Implementation Plan: 045 Test and Mute Notifications

- Migration `0016_account_notifications_muted.sql`: `notifications_muted INTEGER NOT NULL DEFAULT 0`.
- `rows.py` Account field; `app/db/accounts.py` `update_notifications_muted`; `settings_service.set_notifications_muted`.
- `notification_service.send_test(url)` -> `(delivered, error)` via `deliver_webhook`; `check_due_schedules` returns `[]` when the account is muted.
- Routes in `app/routers/settings.py`: `POST /settings/notifications/mute` (checkbox `notifications_muted`, 303 to `/settings`), `POST /settings/notifications/test` (200 delivered / 422 no URL / 502 failed, re-rendering Settings with a message).
- `settings/index.html`: test button in the Webhook panel, mute switch panel, result message region (`role="status"`).
- Tests first: db, `tests/services/test_notification_service.py`, `tests/routers/test_settings.py`.
Constitution v1.3.0: secrets (webhook URL) never logged or echoed; routes thin; pass.
