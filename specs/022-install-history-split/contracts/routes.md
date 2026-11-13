# Interface Contract: 022 Install History Split

Extends `specs/015-component-install-history/contracts/routes.md`.

## New route

| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /bikes/{bike_id}/install-history` | Read-only list of every part that has been on the bike, newest installed first | 200 page | 404 `Bike not found`; sign-in required like every route |

Columns: Part (linked name and kind chip), Placed in, Installed, Removed (or "Still installed"), Actions. Empty state when there are no periods. A "Log a period" button, and Edit (and Delete for removed parts) on rows whose part still exists.

## UI

The bike's action row (`partials/part_actions.html`) gains an "Install history" button beside "Maintenance history" when the screen is a bike.

## Changed behavior (no route change)

- Maintenance history pages (`/bikes/{id}/maintenance`, `/components/{id}/maintenance`) never show automatic add/remove rows (no "Parts" tag).
- `POST /builder/add|move|delete`, `POST /components…`, `POST /bikes/{id}/delete`, and the install-history create and delete routes no longer write maintenance entries.

## Editing from the bike (amendment, 2026-11-12)

| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /bikes/{bike_id}/install-history/new` | Log-a-period form for this bike (part chooser, optional inside-part chooser, install and removal moments) | 200 | 404 `Bike not found` |
| `POST /bikes/{bike_id}/install-history` | Log a closed period of the chosen part on this bike | 303 to `/bikes/{bike_id}/install-history` | 404; 422 form with messages (unknown part, removal not after install, future time, overlap) |
| `GET /install-periods/{id}/edit?from_bike={bike_id}` | The existing edit form; Save and Cancel return to the bike's history | 200 | 404 |
| `POST /install-periods/{id}?from_bike={bike_id}` | The existing update; redirects to the bike's history | 303 | 404; 422 |
| `POST /install-periods/{id}/delete?from_bike={bike_id}` | The existing delete; redirects to the bike's history | 303 | 404; 422 for a live period |

`from_bike` must be a positive integer naming an existing bike; anything else is ignored and the part's history is used.

## Amendment (specs/030-install-history-cleanup)

- `POST /install-periods/{id}` for a still-installed period accepts optional `removed_date`/`removed_time`: a valid moment ends the installation and moves the part (with its sub-parts) to storage at that moment (422 with a message beside `removed_date` when not after the install moment, in the future for the rider's zone, or invalid); blank keeps it installed.
- `POST /install-periods/{id}/delete` also works for a part that has since been deleted. Rows of deleted parts read "(deleted)" and have Delete but no Edit.
- Delete buttons use the normal bordered button style.

