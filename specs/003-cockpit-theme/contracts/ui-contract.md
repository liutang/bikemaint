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

## Amendment (specs/071-ui-consistency)
- Buttons in forms keep their natural width; number/date/time fields and drop-downs are sized to their values; `.form` and `.field` use a `minmax(0, 1fr)` column so nothing pushes a page sideways.
- Cards: `.card-grid` (two columns when wide, one when narrow; `.panel.wide` spans both; a row shares one height and its action buttons sit on the bottom edge).
- One orange `btn-primary` per card for its main action; secondary actions are `btn`.
- Settings cards auto-save through HTMX (`hx-trigger="change"`, card re-rendered with `.save-status` "Saved"/"Not saved"); `<noscript>` Save fallback.
- Row actions Rides/Edit/Delete are `btn btn-icon` with `aria-label` and `title` (icons `route`, `edit`, `trash`).

## Amendments

- **2026-11-18 (feature 084)**: `.sync-status` in the header is empty (`role="img"`, `title` = `aria-label` = hover text). The Strava card has `p.sync-line` with its own dot. The nav link reads "Maintenance". Sign out is `btn btn-icon` with `aria-label` and `title` "Sign out". See `specs/084-quiet-top-bar/`.
- **2026-11-18 (feature 086)**: a usage-triggered due-soon ring shows what's left (`18mi` / `left`, `aria-label="18 miles left"`) and fills by `1 − left / lead`. See `specs/086-usage-lead-time/`.
