# Interface Contract: Outbound Due-Soon Webhook

Sent by the notification check job (contracts/routes.md) as an HTTP `POST` with a JSON body to the user-configured `account.notification_webhook_url` (FR-015, FR-023). The shape is a generic JSON payload with a `content` field so it renders directly in Discord's incoming-webhook format (per the spec's example channel), while remaining plain JSON any other webhook receiver can parse.

## Request

```
POST <user-configured URL>
Content-Type: application/json
```

```json
{
  "content": "🔧 Maintenance due soon: Replace chain on \"Gravel Bike\" — projected 2026-10-02 (approx. 180 mi remaining)",
  "schedule": {
    "id": 42,
    "name": "Replace chain",
    "cycle_number": 3,
    "owner_type": "bike",
    "owner_id": 7,
    "owner_name": "Gravel Bike",
    "projected_due_at": "2026-10-02",
    "projected_remaining_miles": 180.0,
    "is_low_confidence": false
  }
}
```

- `content`: a single human-readable summary line (Constitution Principle V — readable without cross-referencing source), safe to post as-is to a Discord channel webhook.
- `schedule.owner_type`: `"bike"` or `"component"`.
- `schedule.projected_remaining_miles`: omitted (`null`) when the schedule has no mileage interval.
- `schedule.projected_remaining` and `schedule.projected_remaining_unit` (`miles`, `rides` or `hours`): the usage left in the schedule's own unit, `null` for period-only schedules (feature 040). A schedule with Receive notifications off sends nothing.
- `schedule.is_low_confidence`: mirrors FR-018 — true when the projection fell back to time-only or has insufficient ride history.

## Delivery semantics

- One POST per newly-due-soon schedule per check cycle (not batched), matching the `(schedule_id, cycle_number)` dedup key in the data model.
- Timeout 5s, up to 2 retries with backoff; failures are recorded on the `notification` row (`webhook_delivery_error`) and logged, but never block recording the in-app notification itself (research.md §6).
- No response body is expected or parsed; any `2xx` status is treated as delivered.
