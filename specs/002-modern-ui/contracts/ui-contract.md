# UI Contract: Modern UI

This feature adds no routes and changes no request/response data. This contract fixes the
presentation surface that templates, CSS and tests agree on.

## 1. App shell (every page except sign-in)

```html
<a class="skip-link" href="#main">Skip to content</a>
<header class="app-header">
  <nav aria-label="Primary">
    <a class="brand" href="/">BikeMaint</a>
    <a href="/"               [aria-current="page"]>Garage</a>
    <a href="/maintenance/due" [aria-current="page"]>Maintenance due</a>
    <a href="/settings"        [aria-current="page"]>Settings</a>
    <form method="post" action="/logout"><button class="btn btn-quiet">Sign out</button></form>
  </nav>
</header>
<main id="main"> … </main>
```

- The sign-in page renders the same `<header>` with the brand only (no nav links, no sign-out).
- `aria-current="page"` marks the active section per research.md §9.
- Every page has exactly one `<h1>`, a `<title>`, and `<meta name="viewport" content="width=device-width, initial-scale=1">`.

## 2. Design tokens (CSS custom properties on `:root`)

Required token names (values may be tuned, but contrast rules below must hold):
`--bg`, `--surface`, `--surface-2`, `--text`, `--text-muted`, `--border`, `--primary`,
`--primary-text`, `--danger`, `--danger-text`, `--success`, `--warning`, `--info`, and
badge pairs `--badge-overdue-bg/fg`, `--badge-soon-bg/fg`, `--badge-ok-bg/fg`, `--badge-low-bg/fg`.
Each is defined for light on `:root` and overridden inside `@media (prefers-color-scheme: dark)`.

Contrast requirements (checked by `tests/test_ui_contrast.py`, both themes):
`--text` on `--bg` and `--surface` ≥ 4.5:1; `--text-muted` on `--surface` ≥ 4.5:1;
`--primary-text` on `--primary` ≥ 4.5:1; each badge fg on its bg ≥ 4.5:1; `--border` on `--bg`
≥ 3:1 is not required, but focus ring color on `--bg` MUST be ≥ 3:1.

## 3. Class vocabulary

| Class | Use |
|---|---|
| `.container` | centered content column (max ~64 rem) |
| `.card`, `.card-grid` | bike/component cards and their responsive grid |
| `.btn`, `.btn-primary`, `.btn-quiet`, `.btn-danger` | buttons; primary vs secondary vs destructive |
| `.field`, `.field-error`, `.field-hint` | form field wrapper, inline error, hint |
| `.error-summary` | list of form-level errors (`role="alert"`) |
| `.badge`, `.badge-overdue`, `.badge-soon`, `.badge-ok`, `.badge-low` | status badges (always include icon + text) |
| `.tree` | nested component tree (`<details>`/`<summary>` inside) |
| `.table-responsive` | the due-soon table; below ~40 rem rows stack using `data-label` |
| `.empty-state` | empty-state block with heading, text and primary action |
| `.alert` | in-app due-soon alert with a dismiss control |
| `.confirm` | destructive-action confirmation block |

## 4. Status badge mapping

| `status` | Text | Class | Icon |
|---|---|---|---|
| `overdue` | Overdue | `badge-overdue` | warning triangle |
| `due_soon` | Due soon | `badge-soon` | clock |
| `on_track` | On track | `badge-ok` | check |
| `no_estimate` | No estimate yet | `badge-low` | question mark |
| (flag) `is_low_confidence` | Low confidence | `badge-low` | question mark |

## 5. HTMX fragment behavior (existing routes, `hx-request: true`)

| Route | With HTMX | Without HTMX (unchanged) |
|---|---|---|
| `POST /schedules/{id}/complete` | returns the updated `<tr id="schedule-row-{id}">` (already so) | 303 → `/maintenance/due` |
| `POST /notifications/{id}/acknowledge` | returns an empty 200 body; the alert `<li>` is removed via `hx-swap="outerHTML"` | 303 → `/maintenance/due` |
| `POST /bikes/{id}/delete`, `POST /components/{id}/delete` without `confirmed` | returns the `.confirm` fragment, shown inline | returns a full page (layout + `.confirm` block) instead of a bare fragment |

> **Superseded in part**: deleting a bike now needs its typed name (`specs/029-safe-bike-delete`); deleting a part always shows this confirmation, with a Keep install history checkbox (`specs/030-install-history-cleanup`).

Status codes, redirects and data effects are otherwise identical to feature 001's
`contracts/routes.md`.

## 6. Accessibility contract

- Every control has a visible, programmatically associated `<label>`.
- Errors: `aria-invalid="true"` on the control and `aria-describedby` pointing to the error id; the
  summary has `role="alert"`.
- Every interactive element shows a `:focus-visible` outline.
- Tables have `<th scope="col">`; icons are `aria-hidden="true"` and never the only signal.
- `@media (prefers-reduced-motion: reduce)` disables transitions and animations.
