# Phase 0 Research: Modern UI

## 1. Styling approach

- **Decision**: One hand-written stylesheet (`app/static/styles.css`) built on CSS custom
  properties (design tokens), a system font stack, and no framework or compile step.
- **Rationale**: Meets "fast" (one small cacheable file, no web fonts, no images) and "modern"
  (tokens, `color-scheme`, container-friendly grid, `:focus-visible`) with zero new dependencies
  or moving parts, which is what Principle I asks for. The app has ~20 templates; the whole visual
  system fits comfortably under 20 KB.
- **Alternatives considered**: Vendored Pico.css (fast to start but a generic look, and its markup
  conventions would constrain templates); Tailwind standalone CLI (allowed by the amended
  constitution but adds a compile step and a config to maintain for a small app); Bootstrap
  (heavier, JS-oriented components not needed here).

## 2. Light/dark theming

- **Decision**: Define colors as tokens on `:root` for light, override them in
  `@media (prefers-color-scheme: dark)`, and declare `color-scheme: light dark` so native controls
  match. No JavaScript.
- **Rationale**: Follows OS changes live (FR-003), cannot flash the wrong theme, and is the
  simplest possible implementation.
- **Alternatives considered**: A manual toggle with localStorage (out of scope per Assumptions;
  needs JS and persistence).

## 3. Expand/collapse component tree

- **Decision**: Render each node with native `<details open><summary>…</summary>children</details>`
  (leaf nodes are plain list items), indented with a connector line via CSS.
- **Rationale**: Keyboard- and screen-reader-accessible out of the box, works without JavaScript,
  satisfies "collapsed state not remembered".
- **Alternatives considered**: HTMX lazy-loaded branches (needs new routes, violates "no new
  routes"); a JS tree widget (violates Principle I and the stack rules).

## 4. Icons

- **Decision**: A Jinja macro file (`partials/icons.html`) of small inline SVGs, `aria-hidden`,
  paired with visible text labels.
- **Rationale**: No external request, works offline on a self-hosted server, inherits text color so
  themes work automatically.
- **Alternatives considered**: Icon fonts or an icon CDN (extra requests, third-party origin);
  emoji (inconsistent rendering).

## 5. Per-field validation errors that keep the rider's entries

- **Decision**: Add `app/models/form_errors.py` with a function mapping a Pydantic
  `ValidationError` to `{field_name: message}`. Routers pass `field_errors` and `values` (the
  submitted form) to the template in addition to the existing `errors` list, which is kept as the
  summary. A `field` macro renders label, control, hint and error with correct `for`/`id`,
  `aria-invalid` and `aria-describedby`.
- **Rationale**: Delivers FR-009 without changing validation or responses' status codes; existing
  tests that look at `errors` or status 422 keep passing. Errors not tied to a field (service-level
  conflicts such as "a tire is already installed") remain in the summary.
- **Alternatives considered**: Client-side validation JS (violates the no-JS-framework spirit and
  duplicates server rules); leaving errors as a list only (fails FR-009).

## 6. Status badges

- **Decision**: Add a pure function `due_status(projection, lead_time_days, today)` in
  `schedule_service` returning `overdue`, `due_soon`, `on_track` or `no_estimate`; low confidence
  stays a separate flag shown as an extra badge. A `badges.html` macro maps each to icon + text +
  color class.
- **Rationale**: The "due soon" rule (inside the account's lead-time window) is business logic and
  must be testable without HTTP (Principle II); the badge conveys status by text and icon as well
  as color (FR-007, SC-005).
- **Alternatives considered**: Computing status in the template (logic in presentation, untestable
  in isolation).

## 7. In-place updates with HTMX

- **Decision**: Reuse existing partial-update behavior: "Mark done" already returns the row
  fragment. Make `POST /notifications/{id}/acknowledge` return an empty fragment on `hx-request`
  (the alert is removed in place) and make the delete-confirmation flow render the confirmation
  inline on `hx-request`; without HTMX both keep their current redirects / full-page responses
  (the non-HTMX confirm response becomes a full page in the layout instead of a bare fragment).
- **Rationale**: FR-008 and SC-006 with progressive enhancement and no new routes.
- **Alternatives considered**: `hx-boost` on the whole body (changes navigation semantics and
  history handling; not needed).

## 8. Responsive dashboard table

- **Decision**: A semantic `<table>` on wide screens; below ~40 rem the CSS turns each row into a
  stacked card using `data-label` attributes, so there is no horizontal page scroll.
- **Rationale**: Keeps table semantics for assistive technology on desktop and readable rows on
  phones without duplicating markup.
- **Alternatives considered**: Horizontal scroll container (poor on phones, fails SC-003 intent);
  separate mobile markup (duplication).

## 9. Current-section navigation highlight

- **Decision**: Compute the active section in the layout from `request.url.path` and set
  `aria-current="page"` on the matching nav link. Garage covers `/`, `/bikes*`, `/components*`;
  Maintenance due covers `/maintenance/due` and `/schedules*`; Settings covers `/settings*`.
- **Rationale**: No router changes, works for every page including future ones.

## 10. Verification strategy (TDD for a visual feature)

- **Decision**: Test what is objectively checkable: rendered markup (landmarks, labels, badges,
  empty states, tree structure), design-token contrast ratios computed from the stylesheet in both
  themes (WCAG AA, 4.5:1 text and 3:1 UI), presence of `prefers-color-scheme`,
  `prefers-reduced-motion` and `:focus-visible` rules, the asset size budget, and the unchanged
  existing suite. Final look is verified manually in the browser pane at 360 px and 1280 px, light
  and dark.
- **Rationale**: Keeps the TDD gate meaningful for a design change without brittle pixel tests.
- **Alternatives considered**: Screenshot-diff tooling (new dependency and baseline maintenance);
  axe-core in CI (new JS tooling; may be run ad hoc in the browser pane instead).

## 11. Performance

- **Decision**: System font stack, a single stylesheet under 20 KB (budget 40 KB), HTMX loaded with
  `defer`, no images, no external origins, and the existing static-file caching headers.
- **Rationale**: Meets SC-001 trivially for a server-rendered app.
