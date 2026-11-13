# Feature Specification: Storage Part Links

**Feature Branch**: `028-storage-part-links`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User testing feedback (2026-11-13): when a bike or part screen is open, the "In storage" card lists parts in storage; clicking one of those parts should open that part's own info screen (Garage > Storage > <part>).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a Stored Part From the Storage Card (Priority: P1)

As the rider, I want to click a part's name in the "In storage" card and land on that part's own screen, so I can see its details, history and mileage without leaving the bike I'm working on and hunting through the Storage page.

**Why this priority**: It is the whole request, and it removes a dead end: today the names in that card are plain text.

**Independent Test**: Put a spare tire in storage, open any bike, click "Spare tire" in the In storage card: its screen opens with the breadcrumb Garage › Storage › Spare tire.

**Acceptance Scenarios**:

1. **Given** a bike screen with parts in storage, **When** the In storage card is shown, **Then** each part's name is a link to that part's own screen.
2. **Given** a part screen (for example a wheel) with parts in storage, **When** the In storage card is shown, **Then** each stored part's name is likewise a link.
3. **Given** a stored part's screen is opened from the card, **When** it loads, **Then** its breadcrumb reads Garage › Storage › the part's name, with Garage and Storage as links.
4. **Given** the In storage card, **When** the rider drags a stored part, uses its "Add to…" control, or drops a part on the card, **Then** these work exactly as before; making the name a link does not change them.
5. **Given** a stored part's name, **When** the rider drags it by the name, **Then** the part is dragged (not the link address), as when dragging by any other part of the row.
6. **Given** the link, **When** a keyboard or screen reader user reaches it, **Then** it is focusable, operable with Enter, and announced as a link to the part by name.

---

### Edge Cases

- A stored part whose name is long wraps within the card, as it does now.
- A part with sub-parts in storage links to its own screen, where its sub-parts are listed.
- A part that was removed from the card by being installed elsewhere simply disappears from the card; no link is left behind.
- The link must not appear for the part whose own screen is already open (that part is not listed in its own storage card).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On every bike and part screen, the name of each part listed in the "In storage" card MUST be a link to that part's own screen.
- **FR-002**: The opened part screen MUST show the breadcrumb Garage › Storage › the part's name.
- **FR-003**: Dragging a stored part, the "Add to…" control, drop-to-storage and all other behavior of the card MUST be unchanged.
- **FR-004**: The link MUST be reachable and operable by keyboard and exposed to assistive technology as a link with the part's name.

### Key Entities

- **Stored part**: a part with no parent bike or part; unchanged by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any bike or part screen, a stored part's own screen is reachable in one click.
- **SC-002**: 100% of parts listed in the In storage card have a working link; dragging and "Add to…" keep working for 100% of them.

## Assumptions

- The link target is the existing part screen (`/components/{id}`), which already shows the Garage › Storage › part breadcrumb for stored parts; no new screen is needed.
- The card lists the same parts as before; only the name becomes a link.
