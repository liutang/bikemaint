# Quickstart: 084 Quiet Top Bar

1. **Any page:** the top bar reads Garage, Storage, Maintenance, Settings, then a dot and an icon. Hovering the dot reads for example "Sync is working · 7 min ago"; hovering the icon reads "Sign out". On a phone, the bar has no extra row for the sync status.
2. **Settings, Strava connection:** the line under "Connected since…" matches the dot. Turn automatic sync off, and it reads "Automatic sync is off. Last synced …".
3. **Settings, Mute card:** it reads "… under Maintenance."
4. **Sign out** still signs out at once.
5. **Tests:** run `.venv/bin/python -m pytest -q`.
