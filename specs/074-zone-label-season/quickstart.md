# Quickstart: 074 Time Zone Labels Follow the Season

1. **Today (November)**: open Settings → Time zone. New York reads `(GMT-5) America/New York (EST)`, London `(GMT+0) Europe/London (GMT)`, Sydney `(GMT+11) Australia/Sydney (AEDT)`, Auckland `(GMT+13) Pacific/Auckland (NZDT)`.
2. **Summer** (checked in the tests with a fixed July date): New York reads `(GMT-4) … (EDT)`, London `(GMT+1) … (BST)`, Sydney `(GMT+10) … (AEST)`.
3. **Order**: reading down the list, the GMT numbers never go down.
4. **Unchanged**: Phoenix still says "no daylight saving". Saving a zone works as before, and the "Currently …" line matches the selected entry.
5. **Tests**: run `.venv/bin/python -m pytest -q tests/services/test_clock_service.py tests/routers/test_settings.py`.
