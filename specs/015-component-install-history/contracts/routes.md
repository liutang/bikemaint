# Interface Contract: Install History Routes (015)

Extends `specs/001-bike-maintenance-tracker/contracts/routes.md`. All routes require sign-in. Handlers: `app/routers/component_history.py`; logic: `app/services/component_history_service.py`.

| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /components/{component_id}/install-history` | List a part's periods (place, installed, removed, miles) | 200 page | 404 `Part not found` |
| `GET /components/{component_id}/install-history/new` | Log-a-period form | 200 | 404 |
| `POST /components/{component_id}/install-history` | Log a closed period | 303 to the list | 404; 422 re-rendered form with inline errors |
| `GET /install-periods/{period_id}/edit` | Edit form | 200 | 404 `Period not found` |
| `POST /install-periods/{period_id}` | Edit a period (open period: install moment and place only) | 303 to the list | 404; 422 |
| `POST /install-periods/{period_id}/delete` | Delete a closed period | 303 to the list | 404; 422 with plain-text reason when the part is still installed |

## Form fields (create and update)

| Field | Rule |
|---|---|
| `bike_id` | required; must exist (else "Choose a bike from the list.") |
| `parent_component_id` | optional; must exist and differ from the part |
| `installed_date` | required date; not in the future |
| `installed_time` | optional `HH:MM`; a time needs a date |
| `removed_date` | required to log a period; after the install moment; not in the future |
| `removed_time` | optional `HH:MM` |

Errors: overlap with another period, removal not after install, future moments, or a missing removal on a manual period re-render the form with status 422 and a message beside the field.

## Changed route

`POST /builder/add` accepts optional `installed_date` and `installed_time` (blank = now; a time requires a date; not in the future; ignored when `target=storage`). The part's mileage is computed at once from rides on the bike since that moment.
