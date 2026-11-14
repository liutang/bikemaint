# Feature Specification: Component Install Dates and Manual Parts History

**Status**: Implemented on branch `015-component-install-history`

**Input**: (1) When a part is added, let the rider say when it was installed (default now); a part's mileage is the rides between install and removal (or now), cumulative across add/remove cycles and across bikes. (2) Let the rider log and edit a part's past install/removal history by hand, to backfill before production use.

## Findings (existing behavior)
- Per-period attribution already works: `recompute_component_total_mileage` sums rides on each `component_installation_period`'s bike where `installed_at <= ride < removed_at` (open period = until now), plus baseline and adjustments. Example: saddle on bike A 1/1–7/1/2025, then bike B from 9/1/2025 totals A's rides in the first window plus B's rides since 9/1.
- Missing: an install date when adding (always "now"), any way to log or edit periods by hand, overlap validation, and a recompute after back-dating.

## User Story 1 — Install date when adding a part (P1)
Adding a part from the builder's "Add to…" control accepts an optional install date and time.
- **FR-001**: Blank = now. A date alone counts as 00:00; a time requires a date.
- **FR-002**: The install moment cannot be in the future.
- **FR-003**: The new part's mileage is computed at once from rides on the bike (top of its chain) since the install moment.
- **FR-004**: Parts added to storage ignore the date (nothing is installed).

## User Story 2 — Manual parts history (P1)
Each part has an "Install history" screen (`/components/{id}/install-history`) listing its periods (place, installed, removed, miles) and a form to add, edit or delete a period.
- **FR-005**: A logged period names a bike, optionally a parent part on that bike, an install date/time and a removal date/time (past periods are closed; the live period is created by installing). *(Amended by feature 037: the removal may also be left blank to log a period that is still current, see 022.)*
- **FR-006**: The currently open period may have only its install moment and place edited (its removal comes from moving/removing the part); it cannot be deleted by hand-logging a new open period. *(Changed by `specs/030-install-history-cleanup`: filling in a removal moment on the open period now ends the installation and moves the part to storage.)*
- **FR-007**: Periods of one part must not overlap (touching ends are fine). Removal must be after install; neither may be in the future.
- **FR-008**: After any add/edit/delete the part's mileage is recomputed (baseline + rides across all periods + adjustments).
- **FR-009**: Add/delete leave a "Parts" event on the part's maintenance history dated at the logged moment. *(Superseded by `specs/022-install-history-split`: add/delete of a period no longer writes any maintenance entry.)*
- **FR-013** *(added by branch `051-period-boundary-frames`)*: A ride counts toward a period when it started at or after the install moment and before the removal moment, with both read as wall-clock times in the saved time zone: Strava rides are UTC instants and are converted; typed install/removal and manual-ride times are used as typed; moments the app recorded itself are UTC and are converted. Example: a ride at 12:41PM EDT is outside a period installed 12:51PM EDT. Part totals are recomputed at startup so stored totals follow this rule.
- **FR-010**: All routes require sign-in; invalid input re-renders the form with inline errors.

## Assumptions
- Times are stored as typed (no zone conversion), like rides.
- Mileage of a part under a parent part uses the bike chosen on the logged period.

## Amendments
- **2026-11-14 (branch `037-log-open-period`)**: see 022 FR-012; Log a period accepts a blank removal.
- **2026-11-14 (branch `051-period-boundary-frames`)**: FR-013. The old comparison matched Strava UTC times against typed local times, so a ride up to the zone offset before an install (or after a removal) could be counted.
