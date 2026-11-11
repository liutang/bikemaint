# UI Contract: Cockpit Theme (delta over 002-modern-ui)

Everything in `specs/002-modern-ui/contracts/ui-contract.md` still holds unless replaced here.

## Routes
No new routes. `GET /maintenance/due` accepts optional `?all=1` (any other value = off). `POST /schedules/{id}/complete` with `HX-Request` now returns the board partial (`#attention`), not a table row; without it, still 303 to `/maintenance/due`.

## Tokens (names)
`--bg --surface --surface-2 --text --text-muted --border --accent --accent-text --accent-ink --primary(=accent) --focus --danger --success --status-overdue|soon|ok|low-{fg,bg,ring}`; fonts `--font-display`, `--font-sans`.

## Shell
`<header class="app-header">` → `<nav aria-label="Primary">`: `.brand`, pill links (`aria-current="page"` gets accent fill), `.sync-status` (text, `role="status"` not required), sign-out form.

## Attention board
```
<section id="attention" aria-labelledby="attention-heading">
  <div class="attention-grid cols-2|cols-3">      # urgent area, max 6 tiles
    <article class="attention-card status-overdue|status-soon" id="schedule-row-N"> ring • status label • name • owner link • due date • Mark done form
    <a class="attention-more" href="/maintenance/due?all=1">+N more tasks … View all</a>   # only when overflow
  </div>
  <section aria-labelledby="others-heading"><ul class="other-list"> <li id="schedule-row-N"> status badge • name • owner • due • Mark done • Edit • Delete
</section>
```
Ring: `<svg class="ring" role="img" aria-label="Overdue by 30 days">` plus visible `.ring-value` ("30d") and `.ring-caption` ("late"/"left"/"today").
Empty states: `.empty-state` for no schedules; `.all-clear` message when nothing is urgent.

## Status semantics
overdue = red, due soon = gold (distinct hue from accent), on track = green, no estimate/low confidence = grey; each with icon + text.

## Follow-ups
- Due page: no alerts list (FR-022).
- `POST /settings/theme` (form field `theme` = `system|light|dark`): sets the `theme` cookie (1 year, `Secure`, `SameSite=Lax`, `HttpOnly`) and redirects 303 to `/settings`; any other value is 422. `layout.html` renders `<html data-theme="light|dark">` from the cookie (no attribute for System).
- Garage: `.bike-card` (name, type chip, `.bike-card-stat` mileage, primary View + quiet secondary actions); storage components use `.bike-card.is-storage`.
