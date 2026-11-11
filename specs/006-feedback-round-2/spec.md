# Feature Specification: Feedback Round 2

**Feature Branch**: `006-m1-fixes-and-storage`, `007-m2-history-and-polish`, `008-m3-ride-log` (one milestone per branch)

**Created**: 2026-11-11

**Status**: Draft

**Input**: Rider feedback after testing the unified bike screen: (1) deleting a parent part deletes its children; (2) the part screen's palette lists parts that cannot go on that part; (3) maintenance history should log parts being added and removed; (4) history should show time; (5) "Mark done" gives no feedback; (6) a bike needs a ride log with full CRUD; (7) drag a new part into the storage box; (8) the add-part form shows parent IDs; (9) storage is hard to reach and lacks breadcrumbs; (10) the bike and part icons look wrong; (11) maintenance due should name the bike a part belongs to.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deleting and Storing Behave Sensibly (Priority: P1) — Milestone 1

As the rider, I want deleting a part to keep its sub-parts, only the parts that fit to be offered, a way to add parts straight to storage, and storage easy to reach, so I never lose parts by accident or hunt for features.

**Acceptance Scenarios**:

1. **Given** a wheel with a tire and rotor, **When** the rider deletes the wheel (and confirms), **Then** the wheel is deleted and the tire and rotor move to storage with their own sub-parts intact.
2. **Given** a bike with parts, **When** the rider deletes the bike (and confirms), **Then** the bike is deleted and its parts move to storage.
3. **Given** the confirmation for a part that has sub-parts, **When** it appears, **Then** it says the sub-parts will move to storage.
4. **Given** the screen for a wheel, **When** the palette is shown, **Then** it lists only part kinds that can be added to that wheel (tire, rotor, other), and the bike screen lists only kinds that can still be added to the bike.
5. **Given** rotor as a part kind, **When** the palette or forms offer kinds, **Then** rotor is offered and mounts on a wheel.
6. **Given** a bike or part screen, **When** the rider drags a palette part onto the storage box, **Then** a new part of that kind is created in storage.
7. **Given** the Add part form (reached from Storage), **When** it loads, **Then** it shows only name, type and baseline mileage; no parent bike or component ID fields appear and the part is created in storage.
8. **Given** the garage, **When** it loads, **Then** it lists only bikes, with a Storage button (showing how many parts are stored); the top navigation also has a Storage link.
9. **Given** the Storage screen, **When** it loads, **Then** it shows the breadcrumb Garage > Storage, the stored parts, and a button to add a part.
10. **Given** a schedule on a part (for example "Re-wax" on "Chain 1" on "Gravel Bike"), **When** Maintenance due lists it, **Then** the owner reads "Gravel Bike Chain 1"; bike-level schedules show just the bike name.

### User Story 2 - A Useful Maintenance History (Priority: P2) — Milestone 2

As the rider, I want the history to record when parts are added or removed, to show the time of each entry, and "Mark done" to clearly confirm itself.

**Acceptance Scenarios**:

1. **Given** a chain is added to a bike, **When** the history is viewed, **Then** the bike's history shows an entry "Added Chain (chain)" and the chain's history shows "Installed on <bike>", each with date and time.
2. **Given** a tire is taken off a wheel (moved to storage, to another parent, or its parent deleted), **When** the history is viewed, **Then** the wheel's history shows "Removed Tire (tire)" and the tire's shows "Removed from <wheel>".
3. **Given** automatically recorded part events, **When** a part with only those events is deleted, **Then** no extra "has maintenance history" confirmation is triggered by them.
4. **Given** the history table, **When** it loads, **Then** every entry shows its date and time; entries typed in manually take an optional time.
5. **Given** a task on the Maintenance due page (including under "Everything else"), **When** the rider clicks Mark done, **Then** the button is disabled while it works, a confirmation shows "Marked done: <task>. Next due <date>", the task moves to its new position with its new due date, and is briefly highlighted.
6. **Given** a double click or rapid repeat clicks, **When** they are processed, **Then** only one history entry is logged.
7. **Given** any bike or part, **When** its icon is shown (tree rows, palette, storage cards, garage cards), **Then** it is a recognizable drawing: a bike with wheels, frame, saddle and handlebar; a wheel with spokes; a tire; a rotor; a brake caliper; a chain; a saddle; a handlebar; a pedal; a fork; a frame; a drivetrain gear.

### User Story 3 - A Ride Log for Each Bike (Priority: P3) — Milestone 3

As the rider, I want each bike to have a ride log that starts from its base mileage and adds Strava rides, where I can also add, edit, re-assign and delete rides, so the mileage is always right.

**Acceptance Scenarios**:

1. **Given** a bike, **When** the rider opens Rides, **Then** a log shows the starting mileage first, then rides (newest first) with date and time, miles, source (Strava or manual), and a running total ending at the bike's total mileage.
2. **Given** the bike screen, **When** it loads, **Then** a Rides button replaces Adjust mileage (for bikes and for parts).
3. **Given** the ride log, **When** the rider adds a ride (date, optional time, miles, optional note), **Then** it is added as a manual ride and the bike's and its parts' mileage update.
4. **Given** any ride, **When** the rider edits its miles or date, or re-assigns it to another bike, **Then** mileage on both bikes and on the parts installed at that time is recalculated.
5. **Given** a Strava ride the rider edited, re-assigned or deleted, **When** the next sync runs, **Then** the rider's change is kept and the ride is not restored.
6. **Given** a ride is deleted, **When** the log is viewed, **Then** it is gone and mileage is reduced accordingly; deleting asks nothing for a manual ride and nothing extra for Strava rides beyond a clear button.
7. **Given** a part's screen, **When** the rider opens Rides, **Then** a read-only log lists the rides during which that part was installed, with its baseline first.
8. **Given** existing mileage adjustments, **When** totals are computed, **Then** they still count and appear in the log as "Adjustment" rows.

## Requirements *(mandatory)*

- **FR-001**: Deleting a part MUST move its direct sub-parts (with their own sub-parts) to storage; deleting a bike MUST move its parts to storage. Confirmation wording MUST say so.
- **FR-002**: The palette MUST list only part kinds with at least one valid place on the current screen.
- **FR-003**: Rotor MUST be an offered kind mounting on a wheel.
- **FR-004**: Dragging a palette part to the storage box MUST create it in storage.
- **FR-005**: The Add part form MUST NOT show parent IDs; parts it creates go to storage.
- **FR-006**: The garage MUST list only bikes and link to Storage; navigation MUST include Storage; Storage MUST have breadcrumbs and an Add part button.
- **FR-007**: Maintenance due MUST prefix a part's owner with its bike's name; bike-level schedules show the bike alone.
- **FR-008**: Mounting, moving and removing a part MUST log date-and-time events on the parent and on the part; events MUST NOT count as maintenance history for delete confirmations.
- **FR-009**: History MUST show date and time for every entry; manual entries accept an optional time.
- **FR-010**: Mark done MUST give visible feedback, prevent repeat submissions, and log once per click burst; the completed task MUST show its next due date and reposition.
- **FR-011**: Bike and part icons MUST be distinct, recognizable drawings, each with a text label nearby and hidden from assistive technology as decoration.
- **FR-012**: Each bike MUST have a ride log with full create, read, update, delete, re-assignment, a starting-mileage row, running totals and a Rides button replacing Adjust mileage; Strava sync MUST respect rider edits and deletions.
- **FR-013**: Mileage for bikes and parts MUST be recomputed from baseline, rides and adjustments after every ride change, including parts that were on a bike earlier.

## Success Criteria *(mandatory)*

- **SC-001**: Deleting any part never deletes a sub-part.
- **SC-002**: On a part screen, 100% of listed palette kinds can be added there.
- **SC-003**: After one Mark done click, the rider sees a confirmation and the new due date within one second, and the history gains exactly one entry even with repeated clicks.
- **SC-004**: Bike mileage equals starting mileage plus its non-deleted rides plus adjustments in 100% of cases after any ride edit.
- **SC-005**: Existing mileage, schedules and notifications behave as before for unchanged data; the suite passes.

## Assumptions

- Times for events and completed tasks are recorded in UTC and shown in the rider's local time in the browser; typed times are shown as typed.
- "Rides" for a part is read-only and derived from installation periods.
- Existing mileage adjustments stay valid and are shown in the log; the adjust form is no longer linked.
- Milestone 1 branch `006-m1-fixes-and-storage`, milestone 2 `007-m2-history-and-polish`, milestone 3 `008-m3-ride-log`; each is merged, cleaned up and deployed on completion.
