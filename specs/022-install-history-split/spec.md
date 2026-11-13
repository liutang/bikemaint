# Feature Specification: Install History Split From Maintenance History

**Feature Branch**: `022-install-history-split`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User testing feedback (2026-11-12), item 5: component adds and removals should not be part of the maintenance history. Now that there is a separate Install History, component-level installs go there. Bikes should also keep an Install History of what has been added and removed over time. (Decided with the rider: delete the existing automatic add/remove entries from maintenance history rather than hiding them.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintenance History Is Only Maintenance (Priority: P1)

As the rider, I want the maintenance history of a bike or part to list only maintenance work (services I log and tasks I mark done), so I can read it as a service record without parts being added and removed cluttering it.

**Why this priority**: This is the core complaint. Add/remove lines were recorded automatically and mixed in with real work.

**Independent Test**: Add a chain to a bike, move it to storage, delete a tire, then open the bike's and the part's maintenance history: none of those actions appear. Log a service and mark a task done: both appear.

**Acceptance Scenarios**:

1. **Given** a part is added to a bike or another part, **When** the maintenance history of the bike, the parent and the part is viewed, **Then** no "Added…", "Removed…", "Installed on…" or "Removed from…" entry appears.
2. **Given** a part is moved to another parent, to storage, or its parent is deleted, **When** the maintenance histories are viewed, **Then** no entry about the move appears.
3. **Given** the rider logs or deletes an install period by hand on a part's Install History, **When** the maintenance history is viewed, **Then** no entry about it appears.
4. **Given** maintenance histories that already contain automatically recorded add/remove entries, **When** the app is upgraded, **Then** those entries are gone from every maintenance history, and every service the rider logged or completed is still there unchanged.
5. **Given** the rider logs a service or marks a task done, **When** the maintenance history is viewed, **Then** it appears with date and time exactly as before.
6. **Given** a part whose only history was automatic add/remove entries, **When** the rider deletes it, **Then** no "has maintenance history" confirmation is triggered (as already the case).

---

### User Story 2 - A Part's Installs and Removals Live in Its Install History (Priority: P1)

As the rider, I want every install and removal of a part to be found in that part's Install History, so there is one place to see where a part has been.

**Why this priority**: With add/remove entries gone from maintenance history, the part's Install History must be the complete record.

**Independent Test**: Add a part to a bike, move it to another bike, then to storage; its Install History lists three moments in order: installed on bike A, removed and installed on bike B, removed to storage.

**Acceptance Scenarios**:

1. **Given** a part is installed, moved or removed, **When** its Install History is opened, **Then** each period shows where it was, when it was installed and when it was removed (or that it is still installed).
2. **Given** the rider edits or hand-logs a period, **When** the part's Install History is opened, **Then** it reflects the change as it does today.

---

### User Story 3 - A Bike's Install History (Priority: P2)

As the rider, I want each bike to have an Install History showing every part added to or removed from it over time, so I can see how the bike's build has changed.

**Why this priority**: New view that answers "what was on this bike and when". It builds on the same records, so it can ship after the history split.

**Independent Test**: Put a chain on a bike, later move it to storage and add another chain. The bike's Install History lists both chains, newest first: the second chain "still installed", the first with install and removal moments.

**Acceptance Scenarios**:

1. **Given** a bike, **When** its action row is shown, **Then** an "Install history" button sits beside "Maintenance history".
2. **Given** parts have been added to and removed from a bike over time, **When** the bike's Install History is opened, **Then** it lists every period for every part that has been on the bike, including parts nested under other parts, newest first by install moment.
3. **Given** each row, **When** it is read, **Then** it shows the part's name and kind, where it was placed (the bike itself or the part it was inside), the installed date and time, and the removed date and time or "Still installed".
4. **Given** a part that moved from this bike to another, **When** each bike's Install History is viewed, **Then** the first shows the part removed at the move moment and the second shows it installed at that moment.
5. **Given** a part row, **When** the rider selects the part's name, **Then** the part's own screen opens (where its Install History can be edited).
6. **Given** a bike with no parts ever installed, **When** its Install History is opened, **Then** a short empty-state message is shown.
7. **Given** the bike's Install History, **When** it is shown, **Then** the rider can add, edit and delete install periods from it, so past data can be entered retroactively (see User Story 4); each row for an existing part has Edit, and Delete when the part has been removed.
8. **Given** the rider is not signed in, **When** the page is requested, **Then** sign-in is required, as for every other page.

---

---

### User Story 4 - Edit Install History From the Bike (Priority: P2) *(added after user testing)*

As the rider importing old data, I want to add, change and delete install periods straight from a bike's Install History, so I can record when parts were on this bike in the past without opening each part.

**Why this priority**: The rider needs to back-fill history retroactively; doing it part by part is slow, and the bike screen is the natural place.

**Independent Test**: On a bike's Install History choose "Log a period", pick a part, enter an install date and a removal date last spring, save: the row appears in the right place (newest installed first), and the part's own Install History and mileage reflect it.

**Acceptance Scenarios**:

1. **Given** a bike's Install History, **When** it is shown, **Then** a "Log a period" button is offered (also in the empty state).
2. **Given** the Log a period form, **When** it opens, **Then** it names the bike, lets the rider choose any existing part, optionally the part on this bike it was inside, an install date and optional time, and a removal date and optional time.
3. **Given** valid entries, **When** the rider saves, **Then** the period is recorded on this bike for that part, the rider returns to the bike's Install History, and the part's mileage is recalculated as for any period logged from the part.
4. **Given** invalid entries (a removal not after the install, a time in the future, overlapping another period of the same part, an unknown part), **When** the rider saves, **Then** the form is shown again with a clear message beside the field and nothing is recorded.
5. **Given** a row for an existing part, **When** the rider chooses Edit, **Then** the same edit form as the part's Install History opens, and after saving or cancelling the rider returns to the bike's Install History.
6. **Given** a row for a part that has been removed, **When** the rider chooses Delete, **Then** the period is deleted and the rider returns to the bike's Install History; a part that is still installed cannot have its live period deleted by hand (as on the part).
7. **Given** a row for a part that has since been deleted, **When** it is shown, **Then** it is labeled "(deleted)" and offers Delete but not Edit. *(Changed by `specs/030-install-history-cleanup`.)*
8. **Given** edits made from a bike or from a part, **When** either Install History is viewed, **Then** both show the same periods.
9. **Given** the rider is not signed in, **When** any of these pages is requested, **Then** sign-in is required.

---

### Edge Cases

- A part nested several levels deep on a bike appears in that bike's Install History, with the immediate parent as its place.
- A part still installed shows "Still installed" and no removal moment.
- A part moved between two parents on the same bike shows two rows (one closed, one open), newest first.
- A bike deleted by the rider keeps no reachable Install History screen (the bike is gone); its parts' own Install Histories still show their periods.
- Removing the automatic entries must not touch services the rider logged by hand or tasks marked done, even if their text starts with "Added" or "Removed".
- Maintenance histories shown for parts that are deleted later are unaffected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST NOT record any entry in a maintenance history when a part is added, moved, removed or deleted, or when an install period is logged, edited or deleted by hand.
- **FR-002**: On upgrade, the system MUST delete every previously recorded automatic add/remove entry from all maintenance histories, and MUST keep every service the rider logged and every completed task unchanged.
- **FR-003**: Maintenance histories MUST show only maintenance work, with the dates, times, descriptions and mileage they show today.
- **FR-004**: A part's Install History MUST remain the complete record of its installs and removals, with no change to how periods are created, edited, validated or deleted (feature 015).
- **FR-005**: Each bike MUST have an Install History screen, reachable from an "Install history" button beside "Maintenance history" in the bike's action row, requiring sign-in.
- **FR-006**: The bike's Install History MUST list every installation period of every part that has been on that bike, at any depth, newest installed first.
- **FR-007**: Each row MUST show the part's name and kind (by its display name), where it was placed, the installed date and time, and the removed date and time or "Still installed", and MUST link to the part's screen.
- **FR-008**: The bike's Install History MUST let the rider log, edit and delete install periods, with the same validation, mileage recalculation and rules as on a part's Install History (no overlap, removal after install, not in the future, no hand-deleting a live period), and MUST return to the bike's Install History afterwards. *(Changed after user testing: it was first specified read-only.)*
- **FR-009**: A bike with no install periods MUST show an empty-state message.

### Key Entities

- **Installation period**: one stretch during which a part sat in one place on one bike (existing). A bike's Install History is the set of periods whose bike is that bike.
- **Maintenance entry**: a service the rider logged or a task marked done. Automatic add/remove entries no longer exist.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After adding, moving and deleting parts, 0 add/remove lines appear in any maintenance history.
- **SC-002**: 100% of services logged and tasks completed before the upgrade are still present afterwards.
- **SC-003**: For any bike, the number of rows in its Install History equals the number of install periods of parts that have been on it.
- **SC-004**: A rider can see everything that was added to or removed from a bike from a single screen, one click from the bike's page.

## Assumptions

- A bike's Install History is derived from existing installation records; no new data is captured.
- Times are shown as stored, like the part Install History, with no zone conversion (timezone display is handled by a separate feature).
- Automatic entries are identified by how they were recorded (their kind), not by their text.
- This feature supersedes feature 006 FR-008 and the part-event scenarios in 006 User Story 2 (scenarios 1–3).

## Amendments
- **2026-11-12 (branch `024-bike-install-history-editable`)**: the rider needs to back-fill install durations when importing old data, so the bike's Install History is editable (User Story 4; scenario US3-7 and FR-008 changed). Maintenance history entries the rider logs remain editable and are unchanged; only the automatic add/remove rows were removed.
