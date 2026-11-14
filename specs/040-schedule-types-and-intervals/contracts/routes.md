# Routes Contract: 040 Schedule Service Types and Intervals

Extends `specs/001-bike-maintenance-tracker/contracts/routes.md`; paths unchanged.

| Route | Form fields | Success | Failure |
|---|---|---|---|
| `POST /bikes/{id}/schedules`, `POST /components/{id}/schedules` | `service_type` (Charge, Check, Clean, Lube/Wax, Replace, Service, Topup), `interval_kind` (`usage`/`period`), `interval_value` (number > 0), `interval_unit_usage` (`miles`/`rides`/`hours`) or `interval_unit_period` (`years`/`months`/`weeks`) — the one matching `interval_kind` is used, `is_recurring` (checkbox), `notify` (checkbox) | 303 to `/maintenance/due` | 422 form with a message beside the field |
| `POST /schedules/{id}` (edit) | the same plus `is_active` | 303 to `/maintenance/due` | 422; 404 unknown |
| `POST /schedules/{id}/complete` | unchanged | recurring: next cycle; not recurring: schedule ends | 404 unknown |

Old schedules open on Edit with an empty Service Type and a prefilled interval.
