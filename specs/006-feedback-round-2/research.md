# Research: 006 Feedback Round 2 (Retrospective)

Decisions recorded as built across milestones M1 (PR #7), M2 (PR #8) and M3 (PR #9).

## 1. Deleting a part (M1)

- **Decision**: Re-parent a deleted part's direct children to storage, then soft-delete the part. A deleted bike moves its parts to storage the same way. Confirmation wording says so.
- **Rationale**: Cascade deletion silently destroyed parts with mileage and history.
- **Alternatives**: Keep cascade with a stronger warning (still data loss); refuse to delete a part that has children (forces tedious manual moves).

## 2. Palette and placement rules (M1)

- **Decision**: Filter the palette to kinds with at least one valid target on the current screen; add rotor (parents: wheel, hub). Rules stay in `app/models/component_kinds.py`.
- **Rationale**: One source of truth for placement; the UI never offers an impossible drop.
- **Alternatives**: Validate only on drop and show an error (the original frustration).

## 3. Part events versus service entries (M2)

- **Decision**: Add `maintenance_log_entry.kind` (`service` or `event`, default `service`) and optional `performed_time`. Part added/moved/removed write `event` rows on both the parent and the part; only `service` rows count as "has maintenance history" for delete confirmations.
- **Rationale**: One history table, one display, no second log to reconcile; events must not trigger delete warnings.
- **Alternatives**: Separate event table (two histories to merge when displaying); counting events (every delete would warn).

## 4. Time display (M2)

- **Decision**: System-made entries store UTC (`created_at`) and a tiny static script (`localtime.js`) converts to browser-local time; manually typed times display as typed.
- **Rationale**: Avoids storing a timezone per rider while still showing local times.
- **Alternatives**: Server-side zone setting (extra setting for one user).

## 5. Mark done feedback (M2)

- **Decision**: A repeat completion of the same schedule within 5 seconds (`REPEAT_COMPLETION_SECONDS`) is ignored; the form disables its button while submitting; the board shows a notice and highlights the item.
- **Rationale**: Double clicks logged duplicate entries and bumped the cycle twice.
- **Alternatives**: Client-only debounce (does not protect the server).

## 6. Ride log (M3)

- **Decision**: Rebuild `ride_activity` (migration 0009) with nullable `strava_activity_id`, `source`, `note`, `user_modified`, `deleted_by_user`. Sync skips user-modified and user-deleted rides; recompute covers every bike and every part with history on the affected bikes. A ride without a time counts as 12:00; times are stored as typed.
- **Rationale**: One table serves Strava and manual rides, and rider edits must survive the next sync.
- **Alternatives**: Separate manual-ride table (two sources to sum, and edits to Strava rides need an override table anyway); hard-deleting Strava rides (sync would re-import them).

## 7. Spec/branch numbering

- **Decision (retrospective note)**: One spec directory covers three PRs whose branches were numbered 006, 007 and 008. New work uses one spec directory per branch number going forward.
