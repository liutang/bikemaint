# Quickstart: 017 Strava Sync Hardening

Validation guide. Contracts: [contracts/routes.md](contracts/routes.md). Data: [data-model.md](data-model.md).

## Automated (primary)

```bash
.venv/bin/python -m pytest tests/routers/test_strava_pairing.py tests/routers/test_auth.py \
  tests/services/test_strava_client.py tests/services/test_sync_service.py -q
```

Expected: all pass. Map to spec stories: US1 = gear-name, missing-profile, no-bikes, already-paired, stale-token and scope tests; US2 = `test_get_activities_follows_pages_until_a_short_page` and the empty-first-page test; US3 = re-import/unpair tests and `test_backfill_twice_does_not_duplicate_rides`; US4 = the timeout tests.

## Manual (against a real Strava account)

Prerequisites: app running with the variables from `.env.example`.

1. **US1**: Sign in. Open a bike's "Pair with Strava". Expect gear listed by name. To see the missing-access path, revoke BikeMaint in Strava settings, sign in again approving only activity access, and reopen pairing: expect the "Strava did not share your gear list" panel; "Sign out and reconnect" then approve profile access and expect the list.
2. **US2/US3**: Pair a bike with a long history. Note the ride count. Press "Re-import Strava history": expect the same bike screen and an unchanged ride count.
3. **US3**: Press "Unpair from Strava": expect "Pair with Strava" offered again and the rides still present.
4. **US4**: Hard to trigger live; covered by the timeout tests.
