# Feature Specification: "Add a part" Panel With Storage

**Feature Branch**: `033-add-a-part-panel`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback (2026-11-14): consolidate the side panels. The "Add a new part" card becomes "Add a part", and the items in storage become a section inside it, so many stored parts no longer push the part categories down. The rider chose: storage is the last section, behaves like the part categories, collapsed by default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One Panel for Adding Parts, Including Stored Ones (Priority: P1)

As the rider, I want one "Add a part" panel with the part categories and my stored parts as its last section, collapsed like the categories, so the panel stays short and I can still reach stored parts in one place.

**Why this priority**: It is the whole request; it removes a second card and the "pushed down" problem.

**Independent Test**: With many parts in storage, open a bike: the panel shows five category headers and "In storage (N)" below them, all collapsed; open "In storage": the stored parts list, and dragging one onto the bike installs it.

**Acceptance Scenarios**:

1. **Given** a bike or part screen, **When** it is shown, **Then** the side column has one panel titled "Add a part" (not "Add a new part") and no separate "In storage" card.
2. **Given** the panel, **When** it is shown, **Then** it lists the five part categories in the existing order followed by a sixth section "In storage (N)", where N is the number of stored parts; all six are collapsed.
3. **Given** the sections, **When** the rider opens or closes one, **Then** the others do not change; several can be open at once.
4. **Given** "In storage" is opened with stored parts, **When** it is shown, **Then** it lists them exactly as the old card did: the name is a link to the part's screen, the kind chip, a drag handle, and an "Add to…" control where there is a place for it (otherwise "No place for it here yet").
5. **Given** a stored part in the list, **When** it is dragged onto the bike or a part, **Then** it is installed there, as before.
6. **Given** "In storage" is opened and storage is empty, **When** it is shown, **Then** it says "Nothing in storage. Drag a part here to take it off."
7. **Given** a part in the tree, **When** it is dragged onto the "In storage" section, whether the section is collapsed or open (on its header or its list), **Then** the part is taken off the bike and put in storage, as it was on the old card.
8. **Given** a part from the palette, **When** it is dropped onto the "In storage" section, **Then** a new part of that kind is created in storage, as before.
9. **Given** a stored part is dragged, **When** it is dropped onto the "In storage" section, **Then** nothing changes (it is already there).
10. **Given** the section header, **When** used by keyboard or assistive technology, **Then** it opens and closes without a mouse and announces its open state, like the category headers.

---

### Edge Cases

- A count of zero reads "In storage (0)".
- Storing or installing a part updates the count and list when the panel is refreshed after the action.
- While dragging, the "In storage" section is highlighted as a valid drop target like the old card was, even when collapsed.
- The Add-to forms inside storage rows keep their existing behavior.
- The Storage page and the garage's Storage button are unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bike and part screens MUST show a single side panel titled "Add a part" and MUST NOT show a separate "In storage" card.
- **FR-002**: The panel MUST list the five part categories (existing order and contents) followed by an "In storage (N)" section, each collapsed by default and independently openable.
- **FR-003**: The "In storage" section MUST list stored parts as the old card did: name linking to the part's screen, kind chip, drag handle, "Add to…" control or "No place for it here yet", and MUST be draggable to install; empty storage MUST show "Nothing in storage. Drag a part here to take it off."
- **FR-004**: The "In storage" section MUST remain a drop target, collapsed or open: dropping a tree part takes it to storage; dropping a palette part creates it in storage; dropping a stored part changes nothing.
- **FR-005**: The section header MUST be keyboard operable and expose its open state to assistive technology.

### Key Entities

- None new; the section shows the same stored parts as before.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With any number of parts in storage, the closed panel shows exactly 6 headers (5 categories and storage) and no part names.
- **SC-002**: 100% of the drag-and-drop actions that worked with the old storage card (take a part off, create in storage, install from storage) work with the new section.
- **SC-003**: The side column has exactly 1 panel (down from 2).

## Assumptions

- The section reuses the category styling, with the dashed drop-target highlight while dragging.
- Open or closed state is not remembered between page loads (as for the categories).
