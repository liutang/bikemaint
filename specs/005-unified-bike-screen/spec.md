# Feature Specification: Unified Bike Screen and Simpler Parts

**Feature Branch**: `005-unified-bike-screen`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User feedback on features 004: (1) Add bike should take Year, Make, Model (typed) and Category (a drop-down), not a pre-populated make and model list. (2) Add breadcrumb navigation (Garage > Bike > Part) to the bike management screens. (3) Merge the separate view and build screens into one view/edit screen reached from the garage; drop the Build and Add component buttons, and let the remaining buttons (except Pair with Strava) follow the rider as they drill into parts. (4) Part categories are too detailed; the rider tracks mileage on wheels, tires, brakes and similar, not rims and spokes. (5) Every part gets a Garage button (move to storage) and a Trash button (delete).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a Bike by Year, Make, Model and Category (Priority: P1)

As the rider, I want to type the year, make and model of my bike and pick its category from a short list, so I can add any bike, not only ones from a built-in list.

**Why this priority**: Small, self-contained, and it replaces the catalog that does not fit how the rider thinks about their bikes.

**Independent Test**: Open Add a bike, confirm Year, Make and Model are text entries and Category is a drop-down, save, and confirm the bike appears named "Year Make Model" with the chosen category.

**Acceptance Scenarios**:

1. **Given** the Add a bike page, **When** it loads, **Then** it shows Year, Make and Model entry fields, a Category drop-down (road, gravel, mountain, hybrid, e-bike, other), and baseline mileage; there is no list of makes or models.
2. **Given** valid entries, **When** the rider saves, **Then** the bike is named "2022 Trek Domane" (year, make, model) and typed with the chosen category.
3. **Given** a missing make or model, a year that is not a four-digit year between 1900 and next year, or a category outside the list, **When** the rider saves, **Then** the form shows an error beside the field, keeps the other entries, and saves nothing.
4. **Given** a bike with the same name already exists, **When** the rider adds another, **Then** the new bike gets a numeric suffix such as "(2)".
5. **Given** a bike created before this feature (a single free-text name), **When** the rider edits it, **Then** the form explains it has a single name, lets them leave Year, Make and Model blank to keep that name while still changing category and mileage, or fill all three to replace it.
6. **Given** bikes created from the previous built-in catalog, **When** the app starts, **Then** they keep their names and categories.

---

### User Story 2 - Simpler Part Categories (Priority: P2)

As the rider, I care about miles on my wheels, tires, brakes, chain and similar wear items, not on rims, spokes or bolts, so the part categories I can choose from should be few and meaningful.

**Why this priority**: It simplifies the library every other screen uses, so it comes before merging the screens.

**Independent Test**: Open any screen that offers part types; confirm only the simplified list appears, and that existing parts of older types still display and work.

**Acceptance Scenarios**:

1. **Given** any place that offers a part type (the palette, add and edit forms, Move/Add controls), **When** it loads, **Then** it offers only: frame, fork, wheel, tire, brake, drivetrain, chain, pedals, saddle, handlebar and other.
2. **Given** the rules for what mounts on what, **When** a part is added or moved, **Then** tires mount on a wheel; chain mounts on the bike or a drivetrain; every other listed part mounts on the bike; "other" mounts anywhere; storage always works; pedals cannot mount on a wheel.
3. **Given** a bike has two wheels or two brakes (front and rear), **When** the rider adds a second wheel or brake, **Then** it is accepted; frame, fork, drivetrain, chain, pedals, saddle and handlebar stay one per parent, and a wheel holds one tire.
4. **Given** parts of older, finer types (rim, hub, spoke, cassette, rotor, crankset, derailleur, shifter, pad, stem, seatpost, bolt) already exist, **When** they are viewed, moved to storage, deleted or re-ordered, **Then** everything still works, but those types are never offered for new parts.

---

### User Story 3 - One Screen for a Bike and Its Parts (Priority: P3)

As the rider, I want choosing a bike in the garage to open one screen where I see its parts, edit them and build them up, and clicking a part to drill into it on the same kind of screen, with breadcrumbs back up, so I never switch between a "view" screen and a "build" screen.

**Why this priority**: The largest change; it reuses the builder from feature 004 and depends on the simplified part library.

**Independent Test**: Click a bike in the garage; confirm the screen shows the bike's actions, the part tree (drag-and-drop), storage and the palette on one page, with no Build or Add component buttons. Click a part and confirm the same layout scoped to that part, its own actions, and a Garage > Bike > Part breadcrumb.

**Acceptance Scenarios**:

1. **Given** the garage, **When** the rider opens a bike, **Then** one screen shows a breadcrumb (Garage > bike name), the bike's actions (Edit, Maintenance history, Add schedule, Adjust mileage, Pair with Strava when unpaired, Delete), the part tree on the left, and storage and the new-part palette on the right.
2. **Given** that screen, **When** it is inspected, **Then** it has no Build button, no Add component button and no separate build page link; the old build address redirects to the bike screen.
3. **Given** the rider clicks a part, **When** its screen opens, **Then** it shows the breadcrumb Garage > bike > ancestors > part, the same two-pane layout scoped to that part's own sub-parts, and the part's actions (Edit, Maintenance history, Add schedule, Adjust mileage) but not Pair with Strava.
4. **Given** a part in storage, **When** it is opened, **Then** the breadcrumb is Garage > Storage > part and the same layout applies.
5. **Given** every part row (and each part's own header), **When** it is shown, **Then** it has a Garage button that moves it (with its sub-parts) to storage and a Trash button that deletes it.
6. **Given** the rider clicks Trash on a part that has sub-parts, maintenance history or a schedule, **When** the click is processed, **Then** the screen asks for confirmation in place, naming what will be deleted, with a clear Cancel; a part with none of those is deleted at once.
7. **Given** drag and drop, Move to…, Add to… and re-order controls, **When** used on any of these screens, **Then** they behave as in feature 004, limited to the screen's scope, with invalid placements refused and explained.
8. **Given** an old link to a part's separate Move form or to the build page, **When** followed, **Then** it lands on the unified screen.

---

### Edge Cases

- Year typed as text, negative, or in the far future is rejected; leading and trailing spaces in Make and Model are trimmed; very long entries are rejected with a message.
- Deleting a part from its own screen returns to the screen above it (bike or storage).
- A part moved to storage from its own screen shows the storage breadcrumb afterwards.
- Dropping or adding is only allowed within the screen's scope (the bike, or the part and its sub-parts), plus storage for removal.
- A bike with no parts shows a clear "Drag a frame here to start" state.
- The garage page and bike cards no longer offer Build or Add component.
- Existing tests and data for older part types keep working.
- Everything still works without JavaScript through the forms.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add and edit bike MUST take Year, Make, Model (text) and Category (drop-down: road, gravel, mountain, hybrid, e-bike, other); the previous catalog of makes and models MUST be removed.
- **FR-002**: Year MUST be a four-digit year from 1900 to next calendar year; Make and Model MUST be 1 to 60 characters after trimming; invalid input MUST be rejected at the boundary with per-field errors and kept values.
- **FR-003**: A bike's display name MUST be "Year Make Model", with a numeric suffix for duplicates; its type MUST be the category.
- **FR-004**: Bikes created with a single name MUST be preserved; editing one MUST allow keeping the name (all three of Year, Make, Model left blank) or replacing it (all three filled).
- **FR-005**: The offered part types MUST be exactly: frame, fork, wheel, tire, brake, drivetrain, chain, pedals, saddle, handlebar, other.
- **FR-006**: Placement MUST follow: tire on a wheel; chain on the bike or a drivetrain; frame, fork, wheel, brake, drivetrain, pedals, saddle and handlebar on the bike; other anywhere; storage always. Wheel, brake and other MUST allow several per parent; all other offered types one per parent.
- **FR-007**: Parts of older finer types MUST remain fully usable (view, move, delete, re-order) but MUST NOT be offered when creating or changing a part's type; their existing placement rules stay.
- **FR-008**: The bike screen MUST combine viewing, editing and building: breadcrumb, the bike's actions, the part tree with drag and drop, storage, and the new-part palette on one page.
- **FR-009**: Build and Add component buttons and the separate build page MUST be removed; the old build address MUST redirect to the bike screen.
- **FR-010**: Each part MUST have the same unified screen scoped to itself, with its own actions (Edit, Maintenance history, Add schedule, Adjust mileage), omitting Pair with Strava, and the same tree, storage and palette scoped to its sub-parts.
- **FR-011**: Breadcrumbs MUST show Garage > bike > each ancestor > current part (or Garage > Storage > part), every crumb but the last a link, with the current page marked.
- **FR-012**: Every part row and each part's header MUST have a Garage button (move to storage) and a Trash button (delete); Trash MUST ask for confirmation in place when the part has sub-parts, maintenance history or an active schedule, and MUST otherwise delete at once.
- **FR-013**: All drag, Move to…, Add to…, re-order and delete actions MUST be enforced on the server within the screen's scope and MUST keep working without JavaScript.
- **FR-014**: Mileage attribution, maintenance logs, schedules and notifications MUST NOT change behavior.

### Key Entities

- **Bike**: gains year, make and model; its name is derived; its type is the category. The catalog reference is removed.
- **Part kind**: simplified offered set; older kinds retained as hidden.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can add any bike in under 30 seconds with 3 text entries and one drop-down choice.
- **SC-002**: From the garage, a rider reaches any part in at most one click per level of nesting, and can return to any ancestor in one click using the breadcrumb.
- **SC-003**: A rider can add, move, re-order, store and delete parts without leaving the bike's screen.
- **SC-004**: No screen offers more than 11 part types.
- **SC-005**: The existing automated suite passes with no change in mileage, maintenance or schedule behavior.

## Assumptions

- Categories are the five from before plus "other"; no further categories.
- The breadcrumb and unified layout use the Cockpit styling and the same accessibility rules as before.
- The Delete bike action stays on the bike screen; deleting a part from its own screen returns to the level above.
- Older part types are hidden, not migrated; the rider can re-type them by editing.
- Maintenance, schedule, mileage-adjustment and edit pages keep their own screens, reached by the part's buttons.
