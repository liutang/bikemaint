# Quickstart: Cockpit Theme

1. `docker build -t bikemaint:local . && docker rm -f bikemaint; docker run -d --name bikemaint -p 8000:8000 -v bikemaint-data:/data -e SESSION_SECRET_KEY=local-test-secret -e STRAVA_CLIENT_ID=0 -e STRAVA_CLIENT_SECRET=0 bikemaint:local`
2. Seed demo data and sign in with a forged session cookie (see the project README "UI and styling" notes / scratch `seed.py`).
3. Visit `/maintenance/due` in a dark-mode and a light-mode browser: verify charcoal vs cool-grey themes, amber pill + buttons, ring cards (red full ring "Nd late", gold partial arc "Nd left"), compact list below, sync indicator.
4. Add schedules until 7+ are urgent: five cards + "+N more tasks" tile; "View all" shows every urgent task.
5. Mark a card done: board updates in place, no page reload.
6. Check other screens (garage, bike detail tree, forms with errors, settings, login) match.
7. Phone width (375 px): single column, no horizontal scroll.
8. `.venv/bin/python -m pytest -q` is green.
