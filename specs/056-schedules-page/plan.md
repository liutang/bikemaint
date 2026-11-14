# Plan: Schedules Page
- `schedule_service.list_overview_for_owner(kind, id, lead_time_days)` returns `DueItem`s for the item's active schedules (id order) and `interval_text(schedule)` words the interval (typed: "Every 4 months"; older: "Every 186 miles", "Every 30 days").
- Router `schedules.py`: two list routes; `_create` redirects to the owner's list; edit/update/delete honor `from=owner` (a fixed flag, never a URL, so no open redirect). The form context's `cancel_url` follows.
- Templates: `schedules/owner_list.html`; `partials/part_actions.html` swaps Add schedule for Schedules; `schedules/form.html` action keeps `?from=owner`.
Constitution: server-rendered Jinja, no JS, parameterized queries already in `app/db/schedules.py`; logic in the service, routes thin; tests mirror `app/`.
