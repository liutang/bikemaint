# UI Contract: 083 Ride Titles and Activity Types

| Element | Markup |
|---|---|
| Rides list header | `Date & time`, `Title`, `Miles`, `Moving time`, `Activity type`, `Total`, and `Actions` on a bike's list |
| Title cell | `<td data-label="Title">TITLE` plus `<small class="ride-note">NOTE</small>` for a Strava ride with a note |
| Type cell | `<td data-label="Activity type">` with `sport_label(sport_type)`, or `Manual` for `source = 'manual'` |
| Add / manual Edit form | `field("title", "Title", …, hint="Shown in the Rides list.")`, pre-filled `Manual Ride` on Add; no Note field |
| Strava Edit form | `<dl class="readonly-details">` with Title and Activity type, and the hint "From Strava. Rename it there, then Re-import."; Note field kept |
