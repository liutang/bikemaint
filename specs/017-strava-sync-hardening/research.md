# Research: 017 Strava Sync Hardening (Retrospective)

Decisions recorded as built, with the alternatives that were available.

## 1. How to get the rider's gear list

- **Decision**: Request `profile:read_all` together with `activity:read_all` at sign-in. Strava includes the `bikes` list on the athlete only when the profile scope is granted.
- **Rationale**: With only `activity:read_all` the athlete response has no `bikes` key, so pairing showed an empty list with a misleading "refresh your connection" hint.
- **Alternatives**: Read gear ids from each activity (works only for bikes already ridden, gives no names); ask the rider to type a gear id (error prone).

## 2. Telling "missing" from "empty"

- **Decision**: A missing or null `bikes` value raises `StravaGearAccessError`; an empty list is a valid empty result. The router turns the error into a reconnect message with a sign-out button.
- **Rationale**: The two cases need different advice (reconnect vs. add a bike in Strava).
- **Alternatives**: Treat both as empty (the original bug); silently re-request scope (not possible without a new sign-in).

## 3. Paging through activities

- **Decision**: Loop pages of 200 until a page has fewer than 200 items. An exact multiple costs one extra empty request, which is accepted.
- **Rationale**: Simplest correct termination; Strava gives no total count.
- **Alternatives**: Fixed page cap (loses history on large accounts); parallel page fetch (rate limits, needless for one user).

## 4. Timeouts

- **Decision**: 60-second timeout on activity page requests (`ACTIVITIES_TIMEOUT_SECONDS`). The router reports a failure as HTTP 502 with a retry message.
- **Rationale**: The default 5 s limit failed on full-history pages. The manual re-import is the main exposure; background sync retries on its next run.
- **Alternatives**: Smaller page size (more requests, same slow pages); background job with progress UI (over-built for one user).

## 5. Re-import and unpair semantics

- **Decision**: Re-import reuses `sync_service.backfill_bike`; rides are upserted by Strava activity id, so repeats never duplicate. Unpair only clears `strava_gear_id` and `strava_paired_at`; rides and mileage stay.
- **Rationale**: Data the rider already has should never be destroyed by a pairing change.
- **Alternatives**: Delete rides on unpair (data loss); confirmation dialog (extra friction for a reversible action).

## 6. Open items

- Transport errors are caught in the router rather than translated by the service (plan R1).
- Missing logging for the new failure paths (plan R2).
