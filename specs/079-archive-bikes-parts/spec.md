# Feature Specification: Archive Bikes and Parts

**Feature Branch**: `079-archive-bikes-parts`
**Created**: 2026-11-18
**Status**: Draft (the rider asked for it and answered questions on 2026-11-17; not yet approved for planning)
**Input**: The rider, 2026-11-17: "I'd like to spec out the ability to archive bikes and parts." The request asked for:
- **Where archived items show:** collapsed beneath the active ones, in the Garage for bikes and in Storage for parts.
- **Where to archive:** the Edit screen only, "to make it harder to accidentally archive", with wording that explains what archiving does.
- **What archiving does:**
  - All schedules are removed.
  - Rides become read-only.
  - Install history stays usable, "because I can take things off of the archived bike/part".
- **Unarchiving:** an Unarchive button on the archived item's card puts it back in the active state. (Moved to the Edit screen on 2026-11-18, see below.)
  - The rides become editable again.
  - The schedules don't come back.

**The rider's answers, 2026-11-17:**
- **Attached parts:** when archiving, the rider chooses between:
  - keeping the attached parts on it, with their schedules removed;
  - moving all of them to storage, keeping their schedules. "Move to storage should move all parts to storage": every part at every depth goes to storage separately. (Replaced 2026-11-18: sub-parts stay inside, see below.)
- **Only from storage:** only a part in storage can be archived.
- **Strava:** archiving a paired bike unpairs it.
- **Locked:** everything except history.
- **The one action left:** "The only thing that can happen in the install history or the view screen of an archived bike/part is to remove it and move it to storage."
- **How a removal is recorded:**
  - dragging to storage records the removal as now;
  - Install History is the way to back-date a removal;
  - a part removed from an archived item has all its sub-parts split out to storage too, as with "Move to storage". (Replaced 2026-11-18, see below.)

**The rider's changes after the mock-ups, 2026-11-18:**
- **Unarchive moves:** "The un-archive should be in the edit screen and not the main archive screen." Unarchive is a card on the archived item's Edit screen, not a button on its Garage or Storage card.
- **Deleting keeps sub-parts:** "I don't want to split them out when deleting a bike (both active and archived)." Deleting a bike moves its parts to storage with their sub-parts still inside, as today.
- **Archive card layout:** "Option B - horizontal". On the active Edit screen, Strava and Delete stay side by side as today, and the Archive card spans the full width below them.
- **Never split sub-parts:** "Make everything consistent app wide - if a part with sub-parts gets placed into storage, the parts are not split out." This replaces the two splitting answers above. Archiving's "Move to storage" and taking a part off an archived item both move parts with their sub-parts still inside, the same as every other move to storage in the app.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Archive a bike (Priority: P1)

The rider has sold or retired a bike. They want it, and its history, out of the way without deleting anything.

**Why this priority**: It is the main request. Bikes are what fill the Garage.

**Independent Test**: Archive a paired bike that has two schedules and a chain installed, choosing "Move the parts to storage". Check that:
- the Garage lists it only under a closed "Archived (1)" section;
- both of its schedules are gone from Maintenance due;
- the chain is in Storage with its own schedules;
- the bike is unpaired from Strava;
- its rides can be viewed but not added, edited or deleted.

**Acceptance Scenarios**:

1. **Given** an active bike's Edit screen, **Then** it has an "Archive bike" section below the form. The section explains, in plain words, what archiving does:
   - its schedules are removed for good (with the count, for example "2 schedules");
   - its rides become read-only;
   - it is unpaired from Strava (only shown for a paired bike);
   - the only change left possible is taking parts off to storage;
   - it can be unarchived from this Edit screen, but its schedules will not come back.
   
   The Archive card spans the full width below the Strava and Delete cards (mock-up Option B). Without a Strava card, it sits beside Delete.
2. **Given** a bike with parts on it, **Then** the Archive section requires a choice between:
   - **"Keep the parts on the bike"**: their schedules are removed too.
   - **"Move the parts to storage"**: each part directly on the bike goes to storage as of now, with any parts inside it still inside. Every one of them keeps its schedules.
   
   A bike with no parts shows no choice.
3. **Given** the rider presses Archive, **Then** the bike is archived:
   - its schedules, and those of the parts kept on it, are deleted;
   - a paired bike is unpaired, keeping its imported rides;
   - the rider lands on the Garage.
   
   Logged maintenance history is kept.
4. **Given** archived bikes exist, **Then** the Garage lists them below the active bikes in a collapsed "Archived (N)" section, closed on load. Each card has View and Maintenance history buttons, as today, and reads "Archived <date>". With none archived, there is no section.
5. **Given** an archived bike, **When** the rider opens its screen, **Then**:
   - it reads "Archived", with the date;
   - its part tree shows the parts still on it;
   - the "Add a part" panel shows only its "In storage" drop zone;
   - parts can be dragged to storage, and nowhere else;
   - nothing can be added, deleted or moved within it.
6. **Given** an archived bike, **Then** its Rides list is read-only: no Add, Edit or Delete. The routes refuse those changes even when called directly.

---

### User Story 2 - Take parts off an archived bike or part (Priority: P1)

An archived bike still has parts on it that the rider later takes off, for a new bike or to sell.

**Why this priority**: The rider asked for it specifically. Without it, "Keep the parts on the bike" would trap parts on an archived bike.

**Independent Test**: On an archived bike holding a wheelset with a tire inside, drag the wheelset to storage. The wheelset is in Storage, removed now, with the tire still inside it.

**Acceptance Scenarios**:

1. **Given** a part on an archived bike or inside an archived part, **When** the rider drags it to storage, **Then** it is removed as of now and goes to storage with any parts inside it, as anywhere in the app.
2. **Given** an archived bike's Install History, **Then** its still-installed rows have only an Edit that offers the removal date and time. Saving it back-dates the removal, and the part goes to storage with any parts inside it, as when ending a period today (030).
3. **Given** an archived item's Install History, **Then** no period can be logged, and closed periods can't be edited or deleted.
4. **The same limits apply anywhere else a period's place is an archived item**, such as a part's own Install History. Such periods can only be ended, and archived items are never offered in the Bike or Inside part lists of Log or Edit a period.
5. **Given** removed parts that keep schedules, **Then** those schedules continue. Removed parts that were kept on the bike at archiving have none.

---

### User Story 3 - Archive a part (Priority: P2)

The rider retires a worn or spare part that sits in storage.

**Why this priority**: Same need as bikes, but storage clutter matters less.

**Independent Test**: Archive a part in storage that has a schedule. It moves into Storage's closed "Archived (1)" section, its schedule is gone, and it is no longer offered in the builder's storage list or in the "Inside part" list.

**Acceptance Scenarios**:

1. **Given** a part in storage, **Then** its Edit screen has an "Archive part" section with the same explanation as for bikes. If it has parts inside it, the same keep-or-move choice is required.
2. **Given** a part installed on a bike or inside another part, **Then** its Edit screen's Archive section reads "Take this part off to storage before archiving it", with no Archive button.
3. **Given** archived parts exist, **Then** Storage lists them below the active parts in a collapsed "Archived (N)" section, closed on load. Each card reads "Archived <date>".
4. **Given** an archived part, **Then** it is not offered as something to install, and it is not counted in Storage counts:
   - the builder's "In storage (N)" list;
   - the Garage's "Storage (N)" button;
   - the "Inside part" list.

---

### User Story 4 - Unarchive (Priority: P2)

The rider brings a bike or part back into use.

**Why this priority**: Archiving must be reversible, apart from the schedules.

**Independent Test**: Unarchive an archived bike from its Edit screen. It is listed with the active bikes, rides can be added and edited again, it has no schedules, and it can be paired with Strava again.

**Acceptance Scenarios**:

1. **Given** an archived bike's or part's Edit screen, **Then** it has an "Unarchive this bike" (or part) card. The card explains, in plain words:
   - what can be changed again;
   - that the old schedules don't come back;
   - for a bike, that it isn't paired and pairing again imports its rides, including any from while it was archived.
2. **When** the rider presses Unarchive, **Then** the item is active again at once, with no confirmation. It returns to the active list, everything archiving locked is unlocked, and the rider stays on its Edit screen, now editable.
3. **Given** an unarchived bike, **Then**:
   - it has no schedules, and neither do the parts kept on it at archiving;
   - it isn't paired with Strava;
   - pairing it again imports its full history, including rides from while it was archived.

### Edge Cases

- **Delete:** an archived bike or part can still be deleted from its Edit screen. A bike still needs its typed-name confirmation, and a part its existing confirmation.
  - Deleting a bike, active or archived, moves its parts to storage with their sub-parts still inside them, as today.
- **Strava while archived:** the bike is unpaired, so sync brings nothing new. A re-import of the same Strava gear onto another bike could move rides away from it today. While a bike is archived, Strava never changes or moves its rides (the same protection edited rides already have).
- **Maintenance:** no maintenance can be logged on an archived item. Existing entries can be viewed but not edited or deleted. A history that also lists attached parts follows the same rule for rows that belong to the archived item.
- **Mileage:** an archived bike's rides still count toward every part that was on it during them. Taking parts off doesn't change past miles.
- **The Edit screen of an archived item:**
  - it shows its details read-only, with no Save and no Sync rules form;
  - it has no Archive section. A notice reads "Archived <date>. Its details are locked. Unarchive it below to change them.";
  - it has the Unarchive card (US4) and keeps Delete.
- **Backups** include each item's archived state, and restoring brings it back.
- **Notifications:** an archived item has no schedules, so it sends nothing. Parts moved to storage at archiving keep notifying as before.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A bike, or a part in storage, MUST be archivable only from its Edit screen, through an Archive section that explains the effects listed in US1 scenario 1.
- **FR-002**: Archiving an item with attached parts MUST require the choice between:
  - keeping them, with their schedules removed;
  - moving the parts directly on it to storage as of now, with their sub-parts inside, keeping all their schedules.
- **FR-003**: Archiving MUST:
  - delete the item's schedules (and, with "keep", those of its attached parts);
  - record the archive date;
  - unpair a paired bike, keeping its rides.
- **FR-004**: An installed part MUST NOT be archivable.
- **FR-005**: The Garage and Storage MUST list archived items in a collapsed "Archived (N)" section below the active ones, closed on load, absent when empty.
- **FR-006**: An archived item MUST be read-only except for taking attached parts off to storage. This covers:
  - details and sync rules;
  - mileage adjustments;
  - rides (no add, edit or delete);
  - maintenance (no log, edit or delete);
  - schedules (none can be added);
  - parts (none can be added, moved within or deleted);
  - periods whose place is the archived item (no log, edit or delete; a still-installed one may only be ended).

  Every route MUST refuse these changes server-side, including HTMX partial endpoints.
- **FR-007**: Taking a part off an archived item MUST move it to storage with its sub-parts inside, as every move to storage does:
  - by dragging, as now;
  - by ending its still-installed period on Install History, as the typed moment.
- **FR-008**: Archived items MUST be left out of every place a bike or part is chosen as a destination, and out of every Storage count.
- **FR-009**: An archived item's Edit screen MUST have an Unarchive card whose button returns the item to active at once. The Garage and Storage cards MUST NOT have one. Schedules MUST NOT come back, and the bike MUST stay unpaired.
- **FR-010**: Strava sync and re-import MUST NOT change or move the rides of an archived bike.
- **FR-011**: Delete MUST remain available for archived items, with the existing confirmations. Deleting a bike, active or archived, MUST keep moving its parts to storage with their sub-parts inside them.
- **FR-012**: Backup and restore MUST carry the archived state.

### Key Entities

- **Archived state**: on a bike or part, the date it was archived, or none when active.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After archiving, an item appears only in the Archived section, and nothing it held appears on Maintenance due except the schedules of parts moved to storage.
- **SC-002**: Every change route listed in FR-006 refuses a request about an archived item and leaves the data unchanged.
- **SC-003**: Archiving and then unarchiving leaves every ride, install period, maintenance entry and mileage total as it was. Only the schedules are gone, plus the Strava pairing for a bike.
- **SC-004**: No list of places to install a part offers an archived bike or part.

## Assumptions

- **Wording:** the wording on the Archive section, cards and refusals is proposed in the plan and shown to the rider in a mock-up before building, per the rider's rule for visual changes.
- **No confirmation step:** the Archive button needs none beyond its placement on the Edit screen and the required choice. Schedules are lost for good, so the explanation states their count.
- **Unarchive** is only on the Edit screen, as asked, not on the Garage or Storage card or on the item's main screen.
- **Sub-parts are never split out:** every move to storage in the app (archiving, removal from an archived item, delete, and today's moves) keeps a part's sub-parts inside it.
- **Inside parts aren't archived:** parts kept on an archived item are not archived themselves. They stay active parts and can be taken off.
- **Archived parts:** an archived part is always in storage. It may hold parts inside it, if they were kept.
- **Amends:** 001 (Garage), 020/033 (builder and palette), 015/030 (Install History), 006 (rides), 017 (Strava pairing), 029 (bike delete) and 067 (backup). Their own text is noted in the plan.
