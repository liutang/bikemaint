# Routes for 056

| Route | Behavior | Success | Errors |
|---|---|---|---|
| `GET /bikes/{id}/schedules`, `GET /components/{id}/schedules` | The item's active schedules with Add, Edit, Delete | 200 | 404; 303 to /login |
| `POST /bikes/{id}/schedules`, `POST /components/{id}/schedules` | Create (existing); now redirects to the item's Schedules page | 303 | 404; 422 |
| `GET /schedules/{id}/edit?from=owner` | The edit form; Cancel returns to the item's Schedules page | 200 | 404 |
| `POST /schedules/{id}?from=owner` | Update (existing); with `from=owner` redirects to the item's Schedules page | 303 | 404; 422 |
| `POST /schedules/{id}/delete?from=owner` | Delete (existing); with `from=owner` redirects to the item's Schedules page | 303 | 404 |
