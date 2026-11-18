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
- **FR-006**: The currently open period may have only its install moment and place edited (its removal comes from moving/removing the part); it cannot be deleted by hand-logging a new open period. *(Changed by `specs/030-install-history-cleanup`: filling in a removal moment on the open period now ends the installation and moves the part to storage.)* *(Amended by branch `078-open-period-move`: changing the place moves the part there, see FR-014.)*
- **FR-007**: Periods of one part must not overlap (touching ends are fine). Removal must be after install; neither may be in the future.
- **FR-008**: After any add/edit/delete the part's mileage is recomputed (baseline + rides across all periods + adjustments).
- **FR-009**: Add/delete leave a "Parts" event on the part's maintenance history dated at the logged moment. *(Superseded by `specs/022-install-history-split`: add/delete of a period no longer writes any maintenance entry.)*
- **FR-013** *(added by branch `051-period-boundary-frames`)*: A ride counts toward a period when it started at or after the install moment and before the removal moment, with both read as wall-clock times in the saved time zone: Strava rides are UTC instants and are converted; typed install/removal and manual-ride times are used as typed; moments the app recorded itself are UTC and are converted. Example: a ride at 12:41PM EDT is outside a period installed 12:51PM EDT. Part totals are recomputed at startup so stored totals follow this rule. *(Replaced by feature 075: all of these times are UTC instants and are compared directly.)*
- **FR-014** *(added by branch `078-open-period-move`, 2026-11-18)*: Saving the still-installed period with a different Bike or Inside part, and no removal moment, MUST move the part there.
  - **As of the period's install moment:** no new period is added. The edited period says the part has been there since that moment.
  - **Inside parts follow:** every part inside it, at any depth, has its still-installed period switched to the same bike, each keeping its own install moment.
  - **Which bike is recorded:** with an Inside part chosen, the recorded bike is the bike that part is on now (through its parents), or none if it is in storage. The form's Bike field is ignored, as its hint says.
  - **What is refused:** a part can't be placed inside itself or one of its own inside parts. That is refused with the existing message, and nothing changes.
  - **Mileage:** totals are recomputed for every part.
  - **What stays the same:** saving with an unchanged place changes only the install moment, as before. A removal moment entered in the same save ends the period as in 030: the period records the new place and its end, and the part goes to storage.
  - **Acceptance scenarios:**
    1. **Given** a groupset on bike A since 2020-08-30 (still installed), **When** the rider edits that period, picks bike B and saves, **Then** the groupset is on bike B (its breadcrumb and bike B's part tree show it), its Install History has one still-installed row on bike B since 2020-08-30, and its miles are bike B's rides since then.
    2. **Given** a wheel on bike A with a tire inside it, **When** the wheel's still-installed period is changed to bike B, **Then** the tire stays inside the wheel, its still-installed row reads bike B with its own install date, and its miles come from bike B.
    3. **Given** a chain on bike A, **When** its still-installed period is changed to Inside part "Drivetrain", which is on bike B, **Then** the chain is inside the Drivetrain and its row records bike B, whatever the Bike field said.
    4. **Given** a wheel with a tire inside it, **When** the wheel's period is changed to Inside part "Tire", **Then** the form shows the existing "cannot be moved into its own installed sub-tree" error and nothing changes.
    5. **Given** a still-installed period, **When** the rider changes only the install date and saves, **Then** the part stays where it is, as before.
- **FR-010**: All routes require sign-in; invalid input re-renders the form with inline errors.

## Assumptions
- Times are read in the saved zone and stored in UTC, like rides (amended by 075; originally stored as typed).
- Mileage of a part under a parent part uses the bike chosen on the logged period.

## Amendments
- **2026-11-14 (branch `037-log-open-period`)**: see 022 FR-012; Log a period accepts a blank removal.
- **2026-11-14 (branch `051-period-boundary-frames`)**: FR-013. The old comparison matched Strava UTC times against typed local times, so a ride up to the zone offset before an install (or after a removal) could be counted.

## Amendments
- Feature 063: "Inside part (optional)" on Log/Edit a period is a list of parts by name instead of a part-number field (`component_history_service.parent_options`); stored the same way.
- Feature 064: a period inside another part stores no bike; its rides are those on the bikes the parent was on during the overlap (`mileage._WINDOWS`), so a tire in a wheelset earns the wheelset's miles. Parent period changes recompute all parts.
- **2026-11-17 (feature 075)**: FR-013 is replaced. Every install, removal and ride time is a UTC instant (typed ones are read in the saved zone first), so rides and periods are compared as plain instants and the `ride_wall`/`period_wall` rules are retired; see `specs/075-typed-times-utc/`.
- **2026-11-18 (branch `078-open-period-move`)**: FR-014. Editing a still-installed period's Bike or Inside part used to rewrite the period without moving the part, so the part's place (breadcrumb, builder) and its Install History disagreed, and miles came from the period's bike. It was found on the live instance with an Ultegra R8000. An open period inside a part also stored the form's Bike field instead of the bike the part is on.
