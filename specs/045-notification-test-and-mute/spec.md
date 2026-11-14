# Feature Specification: Test and Mute Notifications

**Feature Branch**: `045-notification-test-and-mute`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User testing feedback: "Under Settings → Notifications, add a Test button to test webhook notifications. Also, add a mute notifications option."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Test the Webhook (Priority: P1)

A "Send test notification" button in the Webhook panel posts a short test message to the saved webhook URL and tells the rider whether it arrived.

**Acceptance Scenarios**:

1. **Given** a saved webhook URL that accepts the post, **When** the rider presses the button, **Then** a test message is posted and the page says it was delivered.
2. **Given** a URL that fails (error status or no answer), **When** pressed, **Then** the page says delivery failed and why in plain words (never showing the URL), with a gateway-failure status.
3. **Given** no saved URL, **When** pressed, **Then** the page says to save a webhook URL first, and nothing is sent.
4. **Given** notifications are muted, **When** the rider sends a test, **Then** it is still sent (an explicit test always goes out).
5. **Given** a test, **When** it is sent, **Then** it creates no maintenance notification record and does not change any schedule.

### User Story 2 - Mute Notifications (Priority: P1)

A "Mute notifications" switch on Settings stops all due-soon notifications and webhook posts while it is on. It is off by default.

**Acceptance Scenarios**:

1. **Given** muted, **When** the scheduled check runs, **Then** no notification is recorded and no webhook is sent; schedules still show on Maintenance due.
2. **Given** the switch is turned off again, **When** the next check runs, **Then** anything inside its lead-time window and not yet notified is notified then (nothing was consumed while muted).
3. **Given** the page, **When** shown, **Then** the current state is visible and the switch can be saved; it is validated and stored server-side like other settings.
4. **Given** each schedule's own Receive notifications switch (040), **When** the account is not muted, **Then** that switch still decides per schedule.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Settings MUST offer "Send test notification", posting a test message to the saved webhook URL and reporting delivered, failed (with reason, 502) or no URL (422).
- **FR-002**: The test MUST NOT create notification records, change schedules, or log the URL.
- **FR-003**: The account MUST have a mute setting (default off); while on, `check_due_schedules` MUST record and send nothing.
- **FR-004**: Both routes MUST require sign-in.

### Key Entities

- **Account**: gains `notifications_muted`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can confirm their webhook works in one click.
- **SC-002**: While muted, zero notifications and zero webhook posts are produced.

## Assumptions

- The test message is a Discord-compatible `{"content": ...}` like real alerts.
- Muting is account-wide and independent of per-schedule switches.
