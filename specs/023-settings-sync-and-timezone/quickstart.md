# Quickstart: 023 Strava Sync Settings and Time Zone

## Automated

```bash
.venv/bin/python -m pytest tests/db/test_accounts.py tests/models tests/services/test_settings_service.py \
  tests/services/test_scheduler.py tests/services/test_clock_service.py tests/routers/test_settings.py -q
```

## Manual (after pulling the new image)

1. Settings → Strava connection: set 1 hour 30 minutes, Save. The page says "Every 1 h 30 min".
2. Turn "Sync automatically" off, Save: it says automatic sync is off; the manual sync action still works.
3. Try 0 hours 3 minutes: refused with a message.
4. Settings → Time zone: enter `America/Los_Angeles`, Save. Open the ride log: a Strava ride shows local time with PST/PDT. A manual ride you typed shows exactly as typed.
5. Open a part's install history and try an install moment later today in your zone: refused as future; an earlier moment today is accepted.
