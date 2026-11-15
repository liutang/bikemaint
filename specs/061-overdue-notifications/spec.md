# Feature Specification: Overdue Amount in Notifications

**Feature Branch**: `061-overdue-notifications`
**Created**: 2026-11-15
**Input**: User testing feedback: a notification for an overdue task should say how many days or miles it is overdue, matching what the Maintenance due screen shows (specs/040 FR-012, 055).

## User Scenarios & Testing

### User Story 1 - See How Late in the Notification (Priority: P1)
A rider whose chain is overdue gets a webhook message that says how late it is, the same figure the Maintenance due ring shows.

**Acceptance Scenarios**:
1. **Given** a schedule overdue by date, **Then** the message reads `Maintenance overdue: Topup on "Bontrager RSL51" — projected 2026-08-01 (106d late)`.
2. **Given** a schedule overdue by usage in miles, **Then** the message reads `Maintenance overdue: Lube/Wax on "Revolt chain 2 (Shimano)" — projected 2026-11-14 (27mi late)`; rides use `r` (`3r late`), hours use `h` with one decimal (`2.5h late`).
3. **Given** an overdue schedule with no known amount, **Then** nothing is added after the projected date.
4. **Given** a schedule that is due soon (not overdue), **Then** the message keeps `(approx. N mi remaining)` as before.

### Edge Cases
- An overdue usage schedule never says "approx. 0 mi remaining".
- Amounts use the same rounding as the ring (whole numbers; hours one decimal) and thousands separators.

## Requirements
- **FR-001**: An overdue notification MUST end with `(<amount> late)` using the Maintenance due ring's rules: usage overdue shows the usage over in mi / r / h; otherwise, when the projected date is past, the days late as `Nd`.
- **FR-002**: Overdue with no amount MUST add no parenthesis; due-soon messages MUST keep the existing remaining text.
- **FR-003**: The JSON `schedule` object MAY gain `overdue_amount` and `overdue_unit` (`days`, `miles`, `rides`, `hours`; both `null` when not overdue or unknown) without removing any field.
- **FR-004**: `contracts/webhook-payload.md` (001) MUST describe the new text and fields.

## Success Criteria
- **SC-001**: For every overdue schedule on the Maintenance due screen, the notification text carries the same figure as its ring.

## Assumptions
- Notifications already sent are not changed.
