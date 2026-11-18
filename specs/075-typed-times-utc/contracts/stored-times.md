# Contract: Stored and Displayed Times (075)

This replaces the typed-vs-recorded rules of 015 FR-013, 023 FR-008, 049 and 051.

## Storage

- Every instant is UTC text `YYYY-MM-DDTHH:MM:SS.ffffffZ`, with a four-digit, zero-padded year on every platform (amended by 076, see `specs/076-four-digit-years/contracts/stored-times.md`).
- A time the rider types is read in the saved zone, using the offset on that date (`fold=0`: a nonexistent time uses the offset before the change; a repeated time is the first one), and stored as UTC.
- Default times when the time field is blank:

  | Field | Default |
  |---|---|
  | Ride | 12:00 |
  | Install or removal | 00:00 |
  | Install with date and time both blank | Now |

- An untimed maintenance entry is a local calendar date (`performed_at`), and its `performed_instant` is the end of that local day.

## Comparison

- Rides, install periods, maintenance entries and schedule starting points are compared as plain UTC text.
- The SQL functions `ride_wall` and `period_wall` no longer exist. `part_ride_ok` remains.

## Display

| Value | Filter | Example |
|---|---|---|
| Any instant | `local_time` | `2026-11-16 5:39PM EST` (or `17:39 EST` on the 24-hour clock) |
| Untimed maintenance entry | none | `2026-11-16` |
| Edit-form prefill | `to_local` | `2026-11-16T17:39`, split into date `[:10]` and time `[11:16]` |

The filters `wall_time` and `to_wall` are removed.

## Saving an edit

If the submitted date and minute equal the stored instant's local date and minute, the stored text is kept unchanged (`clock_service.keep_or_convert`).

## Today

`clock_service.today()` is the current date in the saved zone. It drives due dates, days left and late, due-soon notifications and the date Mark done records.

## Routes

No route, form field or status code changes. Pages show the formats above.
