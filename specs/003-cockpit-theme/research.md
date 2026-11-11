# Research: Cockpit Theme

## 1. Token strategy
**Decision**: Keep the existing two-block token structure (`:root` light, `@media (prefers-color-scheme: dark) :root` override) and swap values to the Cockpit palette; add `--accent`, `--accent-text`, `--accent-ink` (darker amber for text-like uses), `--status-*` tokens.
**Rationale**: `tests/test_ui_contrast.py` already parses exactly this shape; every component already reads tokens, so most screens restyle by changing values.
**Alternatives**: separate theme stylesheets (extra request, duplication); CSS `light-dark()` (narrower browser support).

## 2. Palette and contrast
Dark: page `#1b1e25`, surface `#262a33`, surface-2 `#323742`, border `#363c48`, text `#eceef2`, muted `#b8bdc9`. Light: page `#f2f4f8`, surface `#ffffff`, border `#dde1e8`, text `#1b1e25`, muted `#5a6170`. Accent `#FFA800` with dark text `#1b1e25` (about 10:1). `--accent-ink` light `#B45309` (about 5:1 on white) for links/logo/focus; in dark mode accent itself is used for those. Status (dark/light): overdue `#ff8a80`/`#b42318`, due-soon gold `#f5d04a`/`#8a5200` (hue shifted toward yellow, clearly distinct from `#FFA800`), ok `#3ddc84`/`#0a5c39`, low grey. All pairs are asserted in the contrast test.

## 3. Fonts
**Decision**: Vendor Space Grotesk (700/600) and Inter as variable latin-subset `.woff2` under `app/static/fonts/`, loaded with `@font-face` and `font-display: swap`, with system fallbacks. Fetch once at development time (fontsource packages via CDN), commit the files.
**Rationale**: no runtime external request (FR-005), well within the 250 KB budget (about 70 KB). If the download is unavailable the system stack still renders acceptably.
**Alternatives**: Google Fonts link (runtime third-party request, rejected); system fonts only (loses the approved look).

## 4. Rings
**Decision**: One Jinja macro renders an inline SVG ring (track circle + progress circle, `stroke-dasharray`/`stroke-dashoffset` set from a precomputed fraction) with `role="img"` and an `aria-label` such as "Overdue by 30 days" / "Due in 4 days"; the center shows "30d" and the caption "late"/"left" as visible text.
**Fill rule**: overdue = 1.0 (full red). Due soon = `1 - days_left / lead_time_days` clamped to [0.08, 1] so even the farthest due-soon item shows a visible arc; due today = "Today". Overdue by mileage only (no date) shows "Late" in the centre with no number.
**Alternatives**: CSS conic-gradient (poor accessibility story, no stroke caps); canvas/JS (violates simplicity).

## 5. Urgent / overflow split
**Decision**: A pure service function `split_attention(items, show_all, limit=6)` returns `(urgent_shown, overflow_count, others)`. Urgent = status in {overdue, due_soon}; order overdue first (most overdue first) then due soon (soonest first). When urgent count is greater than 6 and not `show_all`: show the first 5 and `overflow_count = n - 5`. `show_all` shows every urgent task.
**Rationale**: matches the approved mockup (5 cards + "+N more" tile = 6 tiles) and keeps logic testable without FastAPI.

## 5b. Columns
Two columns when 1-3 urgent tasks, three columns for 4+ (CSS grid chosen via a modifier class set by the template from the count), one column under 40rem.

## 6. Mark done in place
**Decision**: Cards and list rows live inside one `#attention` region. The HTMX complete request returns the re-rendered board partial (target `#attention`, `outerHTML`), so a completed card moves to the correct place and counts/ordering stay right. A hidden `all` field preserves "View all". Non-HTMX still redirects to `/maintenance/due`.
**Rationale**: swapping a single card cannot relocate it into the other list; swapping the region keeps FR-012 true. Existing tests that assert a single `<tr>` fragment are updated (permitted by FR-019 because the markup is intentionally replaced).

## 7. Last-sync indicator
**Decision**: `app/db/mileage.py` gets `latest_synced_at()` (max `ride_activity.synced_at`); `sync_status_service.last_sync_label(now)` returns "Synced 12 min ago" / "Synced 3 h ago" / "Synced 2 d ago" / "Not synced yet". Exposed to templates as a Jinja global so no router has to pass it.
**Alternatives**: new `account.last_synced_at` column (needs a migration; out of scope for a restyle).
