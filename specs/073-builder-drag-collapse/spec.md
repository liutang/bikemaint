# Feature Specification: Smoother Drag and Collapsible Parts in the Builder

**Feature Branch**: `073-builder-drag-collapse`
**Created**: 2026-11-16
**Status**: Approved prototype ("Build both", 2026-11-16)
**Input**: User testing: "It's very hard to drag-and-drop to reorder. The items don't move around when dragging making it look like the move will add the part as a sub-part instead of a re-ordering." Then: "it needs to be more fluid." and "can you also mock up ability make the trees collapsible? for example, collapse front wheel or roval wheelset?"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See exactly where a dragged part will land (Priority: P1)

The rider drags a part in the "Parts" tree of a bike or part screen. The part lifts out of the list and a gap shaped like it opens where it would land. The rows around it slide to make room, so it is obvious whether the drop puts the part beside a row or inside it.

**Why this priority**: Reordering is the reported problem. Today a reorder and a nest look the same.

**Independent Test**: On a bike with a few parts, drag one part over the rows and check where the gap opens. Drop it and check that the order saved matches where the gap was.

**Acceptance Scenarios**:

1. **Given** a drag has started on a row, **When** the drag begins, **Then** that part and its sub-parts leave the list and a gap of the same height opens in their place. The gap shows the part's icon and name and "on <holder>": the holder part's name, "the bike" on a bike screen, or "this part" on a part screen.
2. **Given** the pointer is in the top 30% of a row, **Then** the gap opens above that row, at the same level.
3. **Given** the pointer is in the bottom 30% of a row with no visible sub-parts, **Then** the gap opens below that row, at the same level. This is the only way to place a part after the last part of a group.
4. **Given** the pointer is in the middle of a row with no visible sub-parts, **Then** the gap opens indented under that row, as its last sub-part.
5. **Given** the pointer is anywhere below the top 30% of a row whose sub-parts are visible, **Then** the gap opens as that row's first sub-part.
6. **Given** the gap moves, **Then** the rows slide to their new places and the gap slides to its new place, in about 0.2 s.
7. **Given** the gap is inside a part, **Then** that part's row is outlined.
8. **Given** the pointer is below every row, **Then** the gap opens as the last top-level part.
9. **Given** the pointer passes through the space between two rows, **Then** the gap stays where it is.
10. **Given** a zone has been chosen on a row, **When** the pointer moves slightly past the zone's edge, **Then** the gap does not move until the pointer is 12% of the row's height past it.
11. **Given** the rider drops, **Then** the part stays where the gap was until the updated tree arrives, and the saved position is the gap's position.
12. **Given** the rider cancels (Escape, or a drop outside the tree), **Then** the list returns to how it was.
13. **Given** a part is dragged from Add a part or from In storage, **Then** the same gap shows where it will be added. Dropping on In storage still moves a part to storage.

---

### User Story 2 - Collapse parts that have sub-parts (Priority: P2)

The rider collapses a part with sub-parts, such as Front wheel or Roval wheelset, to shorten the tree, and opens it again when needed.

**Why this priority**: Long trees make dragging and reading harder, but it is secondary to the reported drag problem.

**Independent Test**: Collapse Front wheel. Check that its sub-parts are hidden and the row says how many it holds. Reload the page and check that it is still collapsed. Open it again.

**Acceptance Scenarios**:

1. **Given** a part with sub-parts, **Then** its row starts with a bordered chevron button that says whether it is open.
   - Its accessible name is "Collapse <name>" when open and "Expand <name>" when collapsed.
   - Its tooltip is "Hide sub-parts" when open and "Show sub-parts" when collapsed.
2. **Given** a part without sub-parts, **Then** its row has an empty space the size of the chevron, so names line up.
3. **Given** the rider clicks the chevron of an open part, **Then** its sub-parts slide closed and the row shows "N parts", where N counts all its sub-parts at every depth ("1 part" for one). Clicking again slides them open and hides the count.
4. **Given** parts were collapsed, **When** the rider moves, adds or removes a part, or reloads the page, **Then** the same parts are still collapsed in that browser.
5. **Given** the browser cannot remember the choice (for example, private mode), **Then** everything shows open and the chevrons still work for the current view.
6. **Given** scripts are off, **Then** every part shows open and nothing is broken.

---

### User Story 3 - Dragging with collapsed parts (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a collapsed part is dragged, **Then** it moves with all its sub-parts.
2. **Given** the pointer is in the middle of a collapsed part's row, **Then** the gap opens alone, indented under that row, as its last sub-part. Its other sub-parts stay hidden.
3. **Given** the pointer stays inside a collapsed part for 0.7 s, **Then** that part opens and the gap becomes its first sub-part.
4. **Given** the rider drops into a collapsed part, **Then** that part shows open afterwards, so the placed part is visible.

### Edge Cases

- **Dragging a part's only sub-part**: the parent's sub-list shows just the gap.
- **Reduce Motion**: the slide follows the rider's own pointer and is short, so it still runs when the system asks for reduced motion. Other animation in the app keeps honoring that setting.
- **Unremembered parts**: a remembered collapsed part that no longer has sub-parts, or no longer exists, has no effect.
- **Refused drop**: the server's refusal message shows as today, and the tree comes back as the server sends it.
- **Non-drag controls**: every control that doesn't use dragging stays and works unchanged: Garage, Trash, Add to…, the Add to… target picker and installed-on fields, and Move to. Tests that cover them are not changed.

## Requirements *(mandatory)*

### Functional Requirements

**Drag feedback (US1, US3)**

- **FR-001**: While dragging, the dragged tree part is hidden from the list together with its sub-parts. A gap of the same height opens where the drop would land. The gap shows the part's icon and name and "on <holder>".
- **FR-002**: Where the drop lands follows the zone rules in US1 scenarios 2–5 and 8–9, with the stickiness rule in scenario 10. Collapsed parts behave as in US3.
- **FR-003**: When the gap moves, rows and the gap slide to their new positions in about 0.2 s. The drop zones are measured from where rows will settle, not from where they are mid-slide.
- **FR-004**: The part that will hold the drop is outlined. When the drop target is storage, the storage section is highlighted instead.
- **FR-005**: A drop sends the same add or move request as today, with the same fields. The server's behavior and its refusal handling don't change.
- **FR-006**: Hovering inside a collapsed part for 0.7 s opens it. Dropping into a collapsed part opens it.

**Collapsible parts (US2)**

- **FR-007**: The server-rendered tree gives every part that has sub-parts a chevron button and a hidden "N parts" count. N is all descendants, with "part" for one and "parts" otherwise. Every other part gets an equal spacer. The script only toggles them.
- **FR-008**: Collapsing hides the sub-parts with a slide, shows the count, sets the chevron's expanded state to false and swaps its accessible name and tooltip. Expanding does the reverse.
- **FR-009**: The set of collapsed parts is remembered per browser and is reapplied after every update of the tree and on page load. If it can't be stored or read, everything shows open.
- **FR-010**: Without scripts, the tree renders fully open, and the chevron does nothing harmful.

### Key Entities

- **Collapsed set**: the ids of the parts collapsed in this browser. It is a viewer convenience, not app data: it is not stored on the server and is not part of backups.

## Success Criteria *(mandatory)*

- **SC-001**: Before dropping, the rider can always tell whether a part will go beside a row or inside it, because the gap's indent and its "on <holder>" label differ.
- **SC-002**: A part can be placed at any position among its siblings, including last, by dragging alone.
- **SC-003**: Moving the pointer steadily down the tree moves the gap through each position once, with no back-and-forth.
- **SC-004**: A collapsed part stays collapsed across reloads and builder actions in the same browser.

## Assumptions

- Only the tree on the bike and part screens changes. The palette and storage lists keep their look.
- Touch devices have no native drag. They keep using the existing Add to… and Move controls.
- The prototype the rider approved on 2026-11-16 is the reference for look and timing.
