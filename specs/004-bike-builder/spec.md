# Feature Specification: Bike Catalog and Interactive Builder

**Feature Branch**: `004-bike-builder`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Two rider requests. (1) Add Bike must not be free text: the rider picks from a curated catalog of common bikes. (2) Interactive bike builder for adding components: a split-screen page per bike (component tree on the left, list of components on the right) with drag and drop to mount, move and re-order components, where components must logically fit (for example pedals cannot be mounted on a wheel), enforced on the server, with a non-drag alternative for every drag action."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick a Bike From a Catalog (Priority: P1)

As the rider, I want to add a bike by choosing a make and model from a list of common bikes instead of typing a name and a type, so my garage is consistent and I never mistype a model.

**Why this priority**: It is self-contained, small, and changes the first thing a rider does in the app.

**Independent Test**: Open Add a bike; confirm there is no free-text name or type field, pick a model, save, and confirm the bike appears with the make and model as its name and the catalog's type.

**Acceptance Scenarios**:

1. **Given** the Add a bike page, **When** it loads, **Then** the rider sees a catalog of common bikes grouped by category (road, gravel, mountain, hybrid, e-bike) and by make, and there is no free-text field for the name or type.
2. **Given** the rider picks "Trek Domane" and saves, **When** the garage loads, **Then** a bike named "Trek Domane" of type "road" (from the catalog) appears.
3. **Given** a bike named "Trek Domane" already exists, **When** the rider adds another Trek Domane, **Then** the new bike is named "Trek Domane (2)".
4. **Given** the rider submits without choosing a catalog entry or with a value that is not in the catalog, **When** the form is processed, **Then** it is rejected with an error beside the field and nothing is saved.
5. **Given** an existing bike whose name is not in the catalog, **When** the rider edits it, **Then** the form offers to keep the current name and type, or to pick a catalog entry instead; baseline mileage stays editable.
6. **Given** a bike was added before this feature, **When** the garage loads, **Then** it is unchanged.

---

### User Story 2 - Components Only Fit Where They Logically Belong (Priority: P2)

As the rider, I want the app to stop me from mounting parts where they cannot go (pedals on a wheel, a tire on a bike frame), and to offer the parts a real bike has, so my component tree always describes a bike that could exist.

**Why this priority**: The rules are what make the builder trustworthy, and they must hold for every way of adding or moving a component, so they come before the interactive page.

**Independent Test**: Using the existing forms, try to add or move components onto valid and invalid parents; invalid ones are refused with a message naming what is allowed; valid ones succeed.

**Acceptance Scenarios**:

1. **Given** a catalog of component kinds with the parents each can mount on, **When** the rider adds or moves a component, **Then** it is accepted only if its parent kind is allowed (bike, a component of an allowed type, or storage).
2. **Given** the rider tries to mount a pedal on a wheel, **When** the request is processed, **Then** it is refused with a message such as "A pedal can be mounted on a crankset, not on a wheel."
3. **Given** a rim, **When** the rider mounts a tire on it, **Then** it is accepted; mounting a tire directly on the bike is refused.
4. **Given** the vocabulary, **When** the rider adds a component, **Then** common bike parts are available (frame, fork, wheel, hub, rim, tire, spoke, cassette, rotor, crankset, pedal, chain, derailleur, shifter, brake, pad, handlebar, stem, seatpost, saddle, bolt, other) and types that already exist in the app keep working.
5. **Given** a parent that already holds one single-instance part of a type, **When** another of that type is mounted there, **Then** it is refused as today; multi-instance types (spoke, bolt, pad, other) still allow several.
6. **Given** existing components arranged before this feature, **When** the app loads, **Then** they remain visible and unchanged even if they would not satisfy a new rule; the rules apply to new adds and moves.
7. **Given** any component can sit in storage, **When** it is unmounted, **Then** it is always accepted.

---

### User Story 3 - Build a Bike by Dragging Parts (Priority: P3)

As the rider, I want a split-screen builder for each bike, with the bike's component tree on the left and the list of components on the right, where I drag parts from the list onto the bike (or onto other parts), move them around, and re-order them, so building a bike feels natural and fast.

**Why this priority**: It is the largest piece and builds on the compatibility rules and catalog vocabulary from Story 2.

**Independent Test**: Open a bike's builder, drag a storage component and a new part from the palette onto valid targets, move a part between parents, re-order siblings, reload to confirm everything persisted, and repeat the same actions using only the keyboard.

**Acceptance Scenarios**:

1. **Given** a bike, **When** the rider opens its builder, **Then** the page is split: the left pane shows the bike with its full component tree; the right pane lists components in storage and a palette of standard part types.
2. **Given** the rider starts dragging a storage component or a palette part, **When** the drag begins, **Then** only valid drop targets in the tree are highlighted and invalid ones are visibly unavailable.
3. **Given** a drag over a valid target, **When** the rider drops, **Then** the component is mounted there (a palette part creates a new component of that type), the tree updates in place without a full page reload, and the change persists.
4. **Given** the rider drops onto an invalid target, **When** the drop is processed, **Then** nothing changes and a clear message explains why.
5. **Given** a mounted component, **When** the rider drags it onto another valid parent, **Then** it moves there with its own sub-tree, and its mileage history keeps being attributed as it is today.
6. **Given** sibling components under one parent, **When** the rider drags one before or after another, **Then** the new order is shown and persists across reloads and on the bike's detail page.
7. **Given** a mounted component, **When** the rider drags it back onto the storage list, **Then** it is removed from the bike into storage.
8. **Given** any drag action, **When** the rider cannot or does not want to drag (keyboard, touch, no JavaScript), **Then** a "Move to…" control on each part lists only valid targets, and choosing one performs the same action; without JavaScript it works through a normal form post.
9. **Given** the builder is open on a narrow screen, **When** it loads, **Then** the two panes stack (tree first, list second) and the Move to… controls remain available.

---

### Edge Cases

- A component cannot be dropped onto itself or onto its own descendants.
- Dropping onto the position it already occupies changes nothing and shows no error.
- A single-instance conflict on drop is reported as a clear message and nothing moves.
- A drop that arrives after another change made the target invalid is re-validated and refused with the current reason.
- Re-ordering applies only among siblings under the same parent; a drop between parents is a move, not a re-order.
- Deleting a bike or component keeps today's confirmation behavior; the builder links to it unchanged.
- An empty bike shows an obvious "Drag a frame here to start" state.
- A catalog entry cannot be forged: only known catalog identifiers are accepted.
- Very long component names wrap inside their tree rows and cards.
- The page remains usable if the drag-and-drop script fails to load.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a curated catalog of common bikes (make, model, category), grouped for easy selection, and Add a bike MUST accept only a catalog entry, with no free-text name or type.
- **FR-002**: A new bike's name MUST be its make and model, its type MUST come from the catalog category, and a duplicate name MUST get a numeric suffix such as "(2)".
- **FR-003**: Editing a bike MUST follow the same rule; a bike whose current name is not in the catalog MAY keep its current name and type until the rider picks a catalog entry. Baseline mileage remains editable.
- **FR-004**: Existing bikes, their names, types and data MUST be unchanged by this feature.
- **FR-005**: The system MUST define, in one place, the catalog of component types and, for each, which parent kinds it may be mounted on (the bike, specific component types, or storage). Storage MUST always be allowed.
- **FR-006**: Every path that creates or moves a component, including the existing forms, the builder, and the Move to… control, MUST enforce the compatibility catalog on the server and refuse invalid placements with a message naming the allowed parents.
- **FR-007**: The existing rule of at most one component per single-instance type under a parent MUST continue to apply, with multi-instance types unchanged.
- **FR-008**: The component vocabulary MUST be extended with common bike parts (at least: fork, cassette, rotor, crankset, pedal, derailleur, shifter, handlebar, stem, seatpost, saddle), keeping all existing types valid.
- **FR-009**: Existing components that predate the rules MUST remain visible and unchanged; the rules apply to new adds and moves, and moving such a component to an invalid parent is refused.
- **FR-010**: Each bike MUST have a builder page with two panes: the bike's component tree (left) and the component list (right) containing components in storage and a palette of standard part types.
- **FR-011**: Dragging a storage component or a palette part onto a valid tree target MUST mount it (a palette part creates a new component with a default name of its type); dragging a mounted component onto another valid target MUST move it with its sub-tree; dragging it to the storage list MUST unmount it.
- **FR-012**: While dragging, the page MUST show which targets are valid and make invalid ones visibly unavailable; invalid drops MUST change nothing and show a clear message.
- **FR-013**: Dragging a component among its siblings MUST re-order them, and the order MUST persist and be used wherever the tree is shown.
- **FR-014**: Every drag action MUST have a non-drag equivalent: a keyboard-accessible Move to… control on each part (and an Add to… control on storage and palette items) listing only valid targets, and working through a normal form post without JavaScript.
- **FR-015**: Tree updates from builder actions MUST happen in place without a full page reload when scripts are available, and MUST fall back to normal navigation otherwise.
- **FR-016**: Moves MUST preserve existing installation-period and mileage attribution behavior; maintenance logs and schedules are unaffected.
- **FR-017**: All input MUST be validated at the boundary: only known catalog and component-type identifiers, existing numeric ids and valid positions are accepted; malformed or forged values are rejected and nothing changes.
- **FR-018**: The builder MUST follow the Cockpit design (both themes, 44 px touch targets, visible focus, WCAG AA contrast, reduced-motion respected) and stack its panes on narrow screens.
- **FR-019**: Drag and drop MUST be implemented as a small hand-written script served as a static asset, with no framework and no build step, per constitution v1.3.0.

### Key Entities

- **Bike catalog entry**: a common bike model with make, model and category; read-only reference data used to create or edit a bike.
- **Component kind**: a component type with its label, whether it is single- or multi-instance, and the parent kinds it may be mounted on.
- **Component**: gains a position among its siblings under a parent; everything else is unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can add a bike in under 20 seconds and 3 interactions (choose, save), with zero typing.
- **SC-002**: 100% of attempts to mount a component on a parent kind outside its allowed list are refused, whichever way they are made (form, drag, Move to…).
- **SC-003**: A rider can build a bike's main structure (frame, wheels with rims and tires, drivetrain) from an empty bike in under 3 minutes using only the builder.
- **SC-004**: Every builder action available by dragging is also available by keyboard alone, verified for mount, move, unmount and re-order.
- **SC-005**: Re-ordered and moved components keep their new place after a reload in 100% of cases.
- **SC-006**: Builder actions update the tree without a full page reload.
- **SC-007**: The existing automated suite passes with no change in tested mileage, maintenance or schedule behavior.

## Assumptions

- "Common bikes" means a curated list of popular models (about 60) from major makes across road, gravel, mountain, hybrid and e-bike categories; it ships with the app and is not editable by the rider.
- Model years are not tracked; one entry per model.
- A bike's name is derived, not typed; the rider has no nickname field in this feature.
- The compatibility catalog is a sensible simplification of real bikes, not an engineering standard; "other" and "bolt" are allowed on any parent, and "pad" on brakes and the bike.
- The palette creates components with the type's default name (for example "Pedal"); renaming uses the existing component edit page.
- Rules apply to new actions; nothing in the existing data is rewritten.
- Touch devices rely on the Move to… control, since native drag and drop is unreliable there.
- Existing partial-update behavior is reused; a few new routes (builder page, builder actions) are expected.
- The work ships in three milestones: catalog (User Story 1), compatibility rules (User Story 2), builder (User Story 3).
