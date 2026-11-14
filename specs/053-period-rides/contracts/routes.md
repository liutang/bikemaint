# Routes added by 053

| Route | Behavior | Success | Errors |
|---|---|---|---|
| `GET /install-periods/{id}/rides[?from_bike={bike_id}]` | Read-only rides that count toward the period; breadcrumb back to the part's install history, or the bike's with `from_bike` | 200 | 404 unknown period; 303 to /login signed out |
