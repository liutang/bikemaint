# Implementation Plan: Usage Lead Time

**Branch**: `086-usage-lead-time` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

- **Settings:** migration `0024_usage_leads.sql` adds `account.lead_miles REAL DEFAULT 20`, `lead_rides INTEGER DEFAULT 2` and `lead_hours REAL DEFAULT 2`.
  - The Lead time card (`settings/cards/lead.html`) shows Days, Miles, Rides and Hours, saved together by `POST /settings/notifications` (`NotificationSettingsRequest` gains the three fields, each 0 or more).
  - Backups carry the new settings (`backup_service.SETTINGS`).
- **One due-soon rule:** `schedule_service.is_due_soon(projection, leads, today)` decides it for both the attention board (`due_status`) and `notification_service.check_due_schedules`. A schedule is due soon when:
  - it isn't overdue, and either
  - its date is within the Days lead, or
  - it's a usage schedule on a bike (`Projection.on_bike`) with what's left at or under its unit's lead, where that lead is above 0.
- **The ring:** for a usage-triggered due soon whose date is later (or missing), the ring shows what's left ("18 mi", "1 ride", "1.5 h") and fills by `1 − left / lead`.
- **Notifications** record `projected_due_at` as the estimated date, or today when there's none. Dedup stays `(schedule_id, cycle_number)`.

Markup is in [contracts/ui-contract.md](contracts/ui-contract.md), and storage in [data-model.md](data-model.md).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: none new
**Storage**: SQLite, migration `0024_usage_leads.sql` (3 columns with defaults)
**Testing**: pytest.
- `is_due_soon` for each trigger, each unit, storage, lead 0, an interval at or under its lead, and period-only schedules.
- Board and notification parity: the same schedules come out due soon from both.
- The Settings card save and refusal.
- A backup round-trip.
- SC-001: SLR7 Chain 3's 2026 cycle replayed, turning due soon at 166 mi.

**Constraints**:
- muting and the per-schedule notify switch still apply;
- the webhook payload is unchanged;
- no script.

**Scale/Scope**: `schedule_service`, `notification_service`, `settings_service`, `requests`, `backup_service`, 3 templates, styles, tests, and amendments to 001, 040, 045, 061, 003's ring contract and CLAUDE.md.

## Constitution Check

- **Fixed stack and layout:** the rule lives in a service function used by both callers, and the settings follow the existing card pattern. PASS
- **I. Simplicity**: one `is_due_soon` instead of two copies. PASS
- **III. TDD**: failing tests first. PASS
- **IV. Security**: the new fields are validated by Pydantic (`ge=0`, an upper bound of 10,000 mi, 1,000 rides or 1,000 h), and SQL is parameterized. PASS
- **V. Observability**: the due-soon log line gains `trigger=date|miles|rides|hours`. PASS
- **Git**: one branch, one PR. PASS

## Project Structure

```text
app/db/migrations/0024_usage_leads.sql
app/db/accounts.py, app/models/rows.py            lead_miles, lead_rides, lead_hours
app/models/requests.py                            NotificationSettingsRequest + 3 fields
app/services/settings_service.py                  set_leads()
app/services/schedule_service.py                  Projection.on_bike, is_due_soon(), due_status() uses it, ring values
app/services/notification_service.py              uses is_due_soon()
app/services/backup_service.py                    SETTINGS += 3
app/templates/settings/cards/lead.html, partials/ring.html (usage left), schedules/due_dashboard.html (if needed)
tests/services/test_schedule_service.py, test_notification_service.py, test_settings_service.py, test_backup_service.py,
tests/routers/test_settings.py, tests/test_ui_attention.py
```

## Before building the screens

The final Lead time card and the usage-left ring go to the rider as a mock-up.

## Complexity Tracking

None.
