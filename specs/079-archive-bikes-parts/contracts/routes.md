# Contract: Routes for Archiving (079)

## New routes

| Route | Form | Result |
|---|---|---|
| `POST /bikes/{bike_id}/archive` | `attached` = `keep` or `move` (required when parts are attached) | 303 to `/`. 422 re-renders the Edit screen when `attached` is missing. 409 if already archived. 404 if no bike. |
| `POST /bikes/{bike_id}/unarchive` | none | 303 to `/bikes/{bike_id}/edit`. 409 if not archived. |
| `POST /components/{component_id}/archive` | `attached` as above | 303 to `/components`. 422 if the part is installed ("Take this part off to storage before archiving it.") or `attached` is missing. |
| `POST /components/{component_id}/unarchive` | none | 303 to `/components/{component_id}/edit`. |

All of them require sign-in.

## Refusals for locked items

Every route that changes a locked bike or part (see research §3) answers **409**:
- **Page forms:** the form re-rendered with the message.
- **HTMX builder actions:** the screen re-rendered with the message.

Nothing is changed.

These still work on a locked item:
- `POST /builder/move` and `POST /components/{id}/move` with target storage;
- `POST /install-periods/{id}` that ends a still-installed period (removal fields only; a place change is refused);
- `POST /bikes/{id}/delete` and `POST /components/{id}/delete` for the archived item itself;
- every GET.

## Changed pages

| Route | Change |
|---|---|
| `GET /` | archived bikes in a closed "Archived (N)" section; Storage count leaves archived parts out |
| `GET /components` | archived parts in a closed "Archived (N)" section |
| `GET /bikes/{id}/edit`, `GET /components/{id}/edit` | Archive card (active); read-only + Unarchive card (archived) |
| `GET /bikes/{id}`, `GET /components/{id}` | archived notice; builder offers only the storage drop |
| `GET /bikes/{id}/rides`, maintenance and install-history lists | no change controls for locked items |
