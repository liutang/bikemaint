# Phase 1 Data Model: Modern UI

This feature is presentation-only: **no tables, columns, migrations or stored data change**
(FR-014, SC-007).

## View-model additions (not persisted)

| Name | Where | Shape | Purpose |
|---|---|---|---|
| `status` | derived by `schedule_service.due_status(projection, lead_time_days, today)` | one of `overdue`, `due_soon`, `on_track`, `no_estimate` | Drives the dashboard status badge (FR-007). Rules below. |
| `is_low_confidence` | existing `Projection` field | bool | Shown as an additional "Low confidence" badge, independent of `status`. |
| `field_errors` | `app/models/form_errors.py` | `dict[str, str]` (field name → first message) | Per-field error text next to the field (FR-009). |
| `values` | router passes the submitted form | `dict[str, str]` | Re-fills the form after a validation error so the rider's entries are preserved. |
| `lead_time_days` | router passes `account.notification_lead_time_days` | int | Lets the row partial compute `status`. |

## `due_status` rules

- `overdue` — `projection.is_overdue` is true.
- `due_soon` — not overdue, `due_at` is set, and `0 <= (due_at - today).days <= lead_time_days`.
- `on_track` — `due_at` is set and further out than the lead-time window.
- `no_estimate` — `due_at` is `None` (mileage-only schedule without enough ride history).

These mirror the notification rule in `notification_service.check_due_schedules` so the badge and
the alert agree.

## Component tree node (template-level)

Existing `build_tree` output (`{"component", "children"}`) is reused unchanged; the template
renders a node with children as `<details open>` and a leaf as a plain list item.
