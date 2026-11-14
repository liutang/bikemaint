# Feature Specification: Schedules Page for a Bike or Part

**Feature Branch**: `056-schedules-page`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback: instead of "Add schedule" on each bike/part, create a "Schedules" button that opens a schedules management page where the rider can add, edit and delete schedules for that particular bike or part. All buttons have borders.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage One Item's Schedules in One Place (Priority: P1)

A bike's or part's screen has a Schedules button (replacing Add schedule). It opens a page listing that item's active schedules, with Add, Edit and Delete.

**Independent Test**: Open a part, choose Schedules, add a Lube/Wax schedule, edit it, delete it; each step returns to the Schedules page.

**Acceptance Scenarios**:
1. **Given** a bike or part screen, **Then** the actions row has a Schedules button linking to `/bikes/{id}/schedules` or `/components/{id}/schedules`, and no Add schedule button.
2. **Given** the Schedules page, **Then** it lists only that item's active schedules with: service type, the interval ("Every 4 months", "Every 186 miles"), Recurring or One-time, notifications On or Off, status and next due (due date, or how far over), and Edit and Delete buttons.
3. **Given** an item with no schedules, **Then** an empty state explains and offers Add schedule.
4. **Given** the page, **When** Add schedule is chosen and the form saved, **Then** the rider returns to this Schedules page with the new schedule listed; Cancel also returns here.
5. **Given** a row, **When** Edit is chosen from this page and saved (or cancelled), **Then** the rider returns here. Edit from Maintenance due still returns to Maintenance due.
6. **Given** a row, **When** Delete is chosen from this page, **Then** the schedule is removed from the list and the rider returns here. Delete from Maintenance due still returns there.
7. **Given** the page, **Then** every button has a border, and it needs sign-in and answers 404 for an unknown bike or part.

## Requirements *(mandatory)*

- **FR-001**: Replace Add schedule on a bike's and a part's actions row with a Schedules button to the item's Schedules page.
- **FR-002**: `GET /bikes/{id}/schedules` and `GET /components/{id}/schedules` MUST show the item's active schedules as in scenario 2, with a breadcrumb back to the item, an Add schedule button (to the existing new-schedule form) and per-row Edit and Delete.
- **FR-003**: Creating a schedule MUST redirect to the item's Schedules page; the new-schedule form's Cancel returns there.
- **FR-004**: Edit and Delete links on the Schedules page carry `from=owner`; with it, saving, cancelling and deleting return to the item's Schedules page; without it, behavior is unchanged (Maintenance due).
- **FR-005**: Routes require sign-in; unknown bike or part is 404.

## Success Criteria
- **SC-001**: A rider can add, edit and delete a schedule without leaving the item's Schedules page between steps.

## Assumptions
- Only active (not deleted) schedules are listed. Delete has no confirmation, as elsewhere.
- Schedules of a part's attached sub-parts are not included (each has its own page).
