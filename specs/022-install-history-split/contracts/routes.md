# Interface Contract: 022 Install History Split

Extends `specs/015-component-install-history/contracts/routes.md`.

## New route

| Method & Path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /bikes/{bike_id}/install-history` | Read-only list of every part that has been on the bike, newest installed first | 200 page | 404 `Bike not found`; sign-in required like every route |

Columns: Part (linked name and kind chip), Placed in, Installed, Removed (or "Still installed"). Empty state when there are no periods. No form controls.

## UI

The bike's action row (`partials/part_actions.html`) gains an "Install history" button beside "Maintenance history" when the screen is a bike.

## Changed behavior (no route change)

- Maintenance history pages (`/bikes/{id}/maintenance`, `/components/{id}/maintenance`) never show automatic add/remove rows (no "Parts" tag).
- `POST /builder/add|move|delete`, `POST /components…`, `POST /bikes/{id}/delete`, and the install-history create and delete routes no longer write maintenance entries.
