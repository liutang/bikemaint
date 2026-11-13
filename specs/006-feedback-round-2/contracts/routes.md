# Interface Contract: Ride Log Routes (006 M3)

Extends `specs/001-bike-maintenance-tracker/contracts/routes.md`. All routes require sign-in. Handlers: `app/routers/rides.py`; logic: `app/services/ride_service.py`. Forms are server-rendered; successful writes redirect with 303.

| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /bikes/{bike_id}/rides` | Ride log: starting mileage row, rides newest first (date and time, miles, source, running total), adjustment rows | 200 page | 404 `Bike not found` |
| `GET /bikes/{bike_id}/rides/new` | Add-ride form | 200 | 404 |
| `POST /bikes/{bike_id}/rides` | Create a manual ride | 303 to `/bikes/{bike_id}/rides` | 404; 422 re-rendered form with inline errors |
| `GET /rides/{ride_id}/edit` | Edit form incl. bike chooser | 200 | 404 `Ride not found` (also for a deleted ride) |
| `POST /rides/{ride_id}` | Edit miles, date, time, note, or re-assign `bike_id` | 303 to the (new) bike's log | 404; 422 |
| `POST /rides/{ride_id}/delete` | Delete a ride (hidden, protected from re-sync) | 303 to the bike's log | 404 |
| `GET /components/{component_id}/rides` | Read-only log of rides while the part was installed, baseline first | 200 | 404 `Component not found` |

## Form fields (create and update)

| Field | Rule |
|---|---|
| `ride_date` | required date |
| `ride_time` | optional `HH:MM` (00:00–23:59) |
| `miles` | required, more than 0 and at most 5000 |
| `note` | optional, at most 200 characters |
| `bike_id` | required on update (choose from the list); ignored on create (taken from the path) |

Blank optional fields count as absent. Validation errors re-render the form with status 422 and a message beside the field.

## Related changes in 006

- `POST /builder/add` accepts `target=storage` (palette drop on the storage box creates a stored part).
- A Rides button replaces "Adjust mileage" on bike and part screens.
- The garage lists bikes only and links to Storage; navigation has a Storage link; Storage has breadcrumbs and an Add part button.
- Delete confirmations for a part or bike say its sub-parts or parts move to storage.
