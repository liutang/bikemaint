# Feature Specification: Maintenance Due Polish

**Feature Branch**: `055-due-polish`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User testing feedback: late cards on Maintenance due have no Delete button; the Delete button on Maintenance history has no border (and, in general, all buttons should have borders); the overdue ring's number must fit inside the ring for any realistic value, at desktop and phone widths.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete From Any Task Card (Priority: P1)

Every task on Maintenance due can be deleted, including the urgent (due soon and overdue) cards, which today offer only Mark done and Edit.

**Acceptance Scenarios**:
1. **Given** an urgent card, **Then** it shows Mark done, Edit and Delete.
2. **Given** Delete is chosen on a card, **Then** the schedule is deleted and the rider returns to Maintenance due.

### User Story 2 - Every Button Has a Border (Priority: P1)

All buttons and button-like links in the app (Sign out, Delete on Rides and Maintenance history, Trash, Add to…, the parts card icon buttons) show a visible border, like Mark done and Edit.

**Acceptance Scenarios**:
1. **Given** any screen, **Then** no button uses the borderless "quiet" style.

### User Story 3 - Ring Numbers Always Fit (Priority: P2)

The number in an overdue progress ring (miles, rides or hours) shrinks as it gets longer so it never touches the ring edge, at desktop and phone widths. Date rings (`5d`, `Today`) look as they do now; the accessible label is unchanged.

**Acceptance Scenarios**:
1. **Given** an overdue value of 5 or more characters (`548mi`, `1991mi`, `12345mi`), **Then** its text is sized by length, relative to the ring's size, so it stays inside the ring.
2. **Given** a date ring, **Then** its size is unchanged.

## Requirements *(mandatory)*

- **FR-001**: Urgent cards MUST offer a Delete button (a separate form posting to `/schedules/{id}/delete`) beside Mark done and Edit.
- **FR-002**: No template MAY use the borderless `btn-quiet` class; the class is removed.
- **FR-003**: Ring values of 5 or more characters MUST get a length class (`n5`..`n8`) that scales the font with the ring size; shorter values are unchanged.
- **FR-004**: The ring's accessible label MUST NOT change.

## Success Criteria
- **SC-001**: A card of any urgency can be deleted in one click.
- **SC-002**: A 7-character ring value stays inside the ring at both ring sizes and at phone width.

## Assumptions
- Delete on a card has no confirmation, like Delete in the other-tasks list.
- Supersedes the quiet-button note in 054 (CLAUDE.md).
