# Implementation Plan: Overdue Amount in Notifications

**Branch**: `061-overdue-notifications` | **Spec**: [spec.md](spec.md)

## Summary
`notification_service.build_webhook_payload` builds the text. For an overdue item it appends `(<amount> late)` using the same rule as `partials/ring.html`: usage `over` with its unit, else days late from `DueItem.days_until`. Not overdue keeps the remaining text.

## Technical Context
Python 3 / FastAPI; no new dependencies, routes or tables. Reuses `format_service.num0/num1`.

## Constitution Check
Stack, layout and TDD unchanged: logic stays in `app/services/notification_service.py`; tests in `tests/services/test_notification_service.py`. No secrets logged. PASS.

## Design
- `_late_text(item) -> tuple[str|None, float|None, str|None]` (text, amount, unit) in `notification_service`.
- Ring rule: overdue and (`days_until` is None or >= 0) and `over` and unit -> usage; elif `days_until` < 0 -> days; else none.
- Payload `schedule` gains `overdue_amount`, `overdue_unit`.

## Artifacts
contracts/webhook-payload.md (001) updated in place; CLAUDE.md note.
