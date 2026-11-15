# Routes for 060

| Route | Behavior | Success | Errors |
|---|---|---|---|
| `POST /bikes/{id}/sync-rules`, `POST /components/{id}/sync-rules` | Save `sport` (repeated), `ride_type` (repeated), `keywords` (text); re-apply to existing rides; redirect to the item's Edit screen | 303 | 404; 422 re-shows the Edit screen with the message beside the field |

Edit screens (`GET /bikes/{id}/edit`, `GET /components/{id}/edit`) gain a Sync rules section.
