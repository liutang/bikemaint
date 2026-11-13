# Feature Specification: Free Part Placement and a Categorised Part Palette

**Feature Branch**: `020-free-placement-and-categories`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User testing feedback (2026-11-12), items 2 and 3: (2) remove the restriction that parts can only be added to logical parents; any part can go on any other part or the main bike, and the bike mechanic decides the hierarchy. (3) the "Add new part" list should be collapsed by category; the rider expands a category and drags the appropriate part to install; several categories can be open or closed at once.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Put Any Part on Any Part (Priority: P1)

As the rider (acting as my own bike mechanic), I want to add or move a part onto any other part or onto the bike, so I can organise the parts tree the way I think about my bike, without the app telling me a part "cannot be mounted" there.

**Why this priority**: The current rules block placements the rider wants and give error messages for them. Removing the blocks is the core request, and the palette change is of little use if parts still cannot go where the rider wants.

**Independent Test**: On a bike with a wheel, drag a chain onto the wheel and a saddle onto a tire; both succeed. Add two chains to the bike; both succeed.

**Acceptance Scenarios**:

1. **Given** a bike and any part, **When** the rider adds a new part or moves an existing part onto that bike, **Then** it is placed there regardless of the part's kind.
2. **Given** any part P and any other part Q (not P itself or one of P's own sub-parts), **When** the rider adds a new part to P or moves Q onto P, **Then** it is placed under P regardless of either kind.
3. **Given** a parent that already holds a part of some kind, **When** the rider adds another part of the same kind to the same parent, **Then** it is added; there is no limit on how many parts of a kind one parent holds.
4. **Given** the "Add to…" and "Move to…" choices, **When** they are listed, **Then** every part on the screen and the bike are offered as targets (excluding a part's own sub-tree when moving), not just "logical" ones.
5. **Given** a drag and drop of a palette part or an existing part onto any row in the parts tree, **When** dropped, **Then** it is placed under that row.
6. **Given** a part, **When** the rider tries to move it onto itself or onto one of its own sub-parts, **Then** it is refused with a clear message and nothing changes.
7. **Given** storage, **When** a part is added or moved there, **Then** it is accepted as before.
8. **Given** parts placed before this change, **When** the screen loads, **Then** every part is in the same place with the same history and mileage as before.

---

### User Story 2 - Pick New Parts From Collapsible Categories (Priority: P2)

As the rider, I want the "Add a new part" list grouped into categories that start collapsed, so I can find a part quickly in a long list and drag it where I want.

**Why this priority**: With free placement and a much longer part list, an ungrouped list becomes hard to scan. It builds on Story 1 but can be delivered separately.

**Independent Test**: Open a bike screen: five collapsed categories show. Expand Brakes and Wheels together, drag "Brake Pads" onto the bike, then collapse Brakes while Wheels stays open.

**Acceptance Scenarios**:

1. **Given** a bike or part screen, **When** it loads, **Then** the palette shows five categories (Accessories, Brakes, Drivetrain, Frame, Wheels), all collapsed.
2. **Given** a collapsed category, **When** the rider expands it, **Then** its parts are listed and can be dragged; expanding or collapsing one category does not change any other.
3. **Given** several categories expanded, **When** the rider collapses one, **Then** the others stay expanded.
4. **Given** the palette, **When** the rider expands each category, **Then** it lists exactly these parts, in this order:
   - Accessories: Accessories, Apparel, Computer, Lights
   - Brakes: Brake, Brake Cable, Brake Lever, Brake Pads, Rotor
   - Drivetrain: Bottom Bracket, Cassette, Chain, Chainrings, Crankset, Derailleur, Pedals, Shift levers, Shifter Cable
   - Frame: Fork, Frame, Handlebar, Handlebar Tape, Headset, Saddle, Seatpost, Shock, Stem
   - Wheels: Axle, Hub, Trainer, Tube, Tire, Wheel, Wheel Set
5. **Given** any part in the palette, **When** it is dragged onto the bike, any part, or the storage box, **Then** a new part of that kind is created there.
6. **Given** the palette on any screen, **When** it is shown, **Then** all categories and parts are listed (the list is no longer reduced to parts that "fit" the current screen).
7. **Given** a keyboard or touch user, **When** they use a category header, **Then** it can be expanded and collapsed without a mouse, and its expanded state is announced to assistive technology.
8. **Given** the palette, **When** it is shown in light or dark mode, **Then** each category header looks like the app's other panels (bordered, rounded, matching text) with a clear expand/collapse arrow, not the browser's bare marker. *(Confirmed by the rider on 2026-11-12 once the new styles loaded.)*
9. **Given** the app was upgraded while the rider's browser still holds the previous version's files, **When** the rider opens any page, **Then** the new styles and drag-and-drop script are used on that first load (no hard refresh needed), so dragging a palette part onto the bike, a part or storage works.

---

### Edge Cases

- Parts that already exist with kinds no longer in the palette (the older "drivetrain" and "other part", and finer legacy kinds such as spoke, rim and bolt) keep working: they display with their own names, keep their data, and can be moved, renamed, scheduled and deleted.
- Parts of an existing kind that matches a palette entry (for example an existing pedal, shifter or brake pad) show under the palette's name for that part and are otherwise unchanged.
- Deleting a part keeps its sub-parts (they move to storage), as in feature 006.
- A part cannot be a parent of the part above it; cycles are refused (Story 1, scenario 6).
- Placing a part under another part changes mileage attribution only through the existing rule that a part's mileage follows the bike at the top of its chain.
- The earlier "one of this kind per parent" message ("can be mounted on …") is never shown for placement any more.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow any part to be added to or moved onto the bike or onto any other part, regardless of kind, with these exceptions only: a part cannot be placed under itself or under one of its own sub-parts.
- **FR-002**: The system MUST NOT limit how many parts of the same kind a single parent holds.
- **FR-003**: Storage MUST continue to accept any part.
- **FR-004**: Every place that offers placement targets (add-to, move-to, drag and drop, the add-part form) MUST offer all valid targets under FR-001.
- **FR-005**: The "Add a new part" palette MUST be grouped into the categories Accessories, Brakes, Drivetrain, Frame and Wheels, each collapsible, all collapsed when a screen loads.
- **FR-006**: Categories MUST expand and collapse independently of each other, several open at once.
- **FR-007**: The palette MUST offer exactly the parts listed in User Story 2, scenario 4, in the order given, under their categories.
- **FR-008**: The palette MUST list all categories and parts on every bike and part screen, not only those valid for the current screen.
- **FR-009**: Parts of kinds that are no longer offered MUST keep working everywhere (display, edit, move, schedules, mileage, history, delete) and MUST NOT lose data.
- **FR-010**: Each category header MUST be operable by keyboard and expose its expanded or collapsed state to assistive technology.
- **FR-011**: Placement refusals MUST say why in plain language (for example, a part cannot be placed inside itself).
- **FR-012**: Placing, moving and removing parts MUST continue to record installation periods and recompute mileage as before.
- **FR-013**: Category headers MUST be styled consistently with the app's other panels, with an arrow that reflects the open or closed state. *(Added after user testing, 2026-11-12.)*
- **FR-014**: Stylesheets and scripts MUST be requested by addresses that change whenever their content changes, so a browser never keeps using an outdated copy after an upgrade. *(Added after user testing, 2026-11-12; found when drag-and-drop failed and the new header styles were missing because the browser kept old files.)*

### Key Entities

- **Part kind (catalog entry)**: a part's type with a display name and a category. A kind is "offered" (shown in the palette) or "legacy" (valid on existing parts, never offered). Kinds no longer carry placement rules or a one-per-parent limit.
- **Category**: one of Accessories, Brakes, Drivetrain, Frame, Wheels; an ordered group of offered kinds.
- **Part**: unchanged apart from where it may be placed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In user testing, the rider can place any part under any other part or the bike on the first attempt, with zero "cannot be mounted" refusals.
- **SC-002**: 100% of placements that do not put a part inside itself or its own sub-parts succeed.
- **SC-003**: A rider can reach and drag any one of the 34 palette parts in at most two interactions (expand its category, drag it).
- **SC-004**: With the palette first shown, no more than 5 category headers are visible and no part names are, so a bike screen with a full parts tree is not pushed down by the palette.
- **SC-005**: All parts, mileage, schedules and histories that existed before the change are unchanged afterwards (suite passes; no data migration loss).

## Assumptions

- Open and closed state is not remembered between page loads; each load starts with all categories collapsed. (Reload or navigation resets it.)
- The palette's names are the display names; where a palette name matches an existing kind, parts of that kind show that name (Pedals, Shift levers, Brake Pads and so on) and are otherwise unchanged. New kinds start with no parts.
- Other places that list part types (for example the add-part form's type choice) use the same list and category order.
- The "Add to…" and "Move to…" menus are not categorised; only the palette is.
- The rider is the only user; there is no per-bike permission or rule configuration.
- This feature reverses the placement rules and one-per-parent behavior defined in specs 004 and 005; those specs are superseded for placement by this one.

## Amendments
- **2026-11-12 (branch `021-fix-palette-drag-and-style`)**: user testing found (a) dragging a palette part no longer worked and (b) category headers looked unstyled. Cause: the browser kept the previous release's `builder.js` and `styles.css`. Added scenarios US2-8 and US2-9 and FR-013/FR-014.
