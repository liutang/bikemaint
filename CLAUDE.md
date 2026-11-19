# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

The 001 feature is implemented (all tasks in `tasks.md` are checked off). Common commands, from the repo root:

- Install: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Test: `.venv/bin/python -m pytest -q` (single file: `pytest tests/services/test_x.py`)
- Run: export the variables in `.env.example`, then `uvicorn app.main:app --reload`
- Docker: `docker build -t bikemaint:local .` (see README "Running in Docker")

All features so far are merged into `master`; new work goes on a short-lived feature branch cut from it. **Every change, however small, goes through the Spec Kit skills first** (`/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`, test-first), with its own `specs/NNN-name/`; never merge code without one. Branch and spec numbers are sequential and must match. Spec chains live under `specs/`: `001-bike-maintenance-tracker` (the app), `002-modern-ui` and `003-cockpit-theme` (the UI). The 001 chain contains:
- `spec.md` — feature spec (user stories, functional requirements, clarifications)
- `plan.md` — implementation plan (tech stack choices, constitution gate check, source layout)
- `research.md` — Phase 0 design decisions and rejected alternatives
- `data-model.md` — SQLite schema/entities
- `contracts/routes.md`, `contracts/webhook-payload.md` — HTTP route contract and outbound webhook contract
- `quickstart.md` — end-to-end manual validation script per user story
- `tasks.md` — the dependency-ordered task list that was implemented

## Spec Kit workflow

This project uses [GitHub Spec Kit](https://github.com/github/spec-kit) for spec-driven development, invoked as slash-command skills. The intended cycle per feature is:

1. `/speckit-constitution` — create/amend `.specify/memory/constitution.md` (project-wide governance; rare, deliberate).
2. `/speckit-specify` — create/update a feature's `spec.md` from a natural-language description.
3. `/speckit-clarify` — resolve ambiguous areas of a spec via targeted Q&A before planning (already run once for 001-bike-maintenance-tracker; see its Clarifications section).
4. `/speckit-checklist` — generate a custom requirements-quality checklist for a feature.
5. `/speckit-plan` — generate `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` from the spec + constitution.
6. `/speckit-tasks` — generate `tasks.md`, a dependency-ordered task breakdown, from the plan/design artifacts.
7. `/speckit-analyze` — non-destructive cross-check of spec.md/plan.md/tasks.md for consistency before implementing.
8. `/speckit-implement` — execute `tasks.md` against the codebase.
9. `/speckit-converge` — after ad hoc changes, diff the codebase against spec/plan/tasks and append any unbuilt work as new tasks.
10. `/speckit-taskstoissues` — convert `tasks.md` entries into GitHub issues.

Each feature lives under `specs/NNN-feature-name/`, numbered sequentially; `.specify/scripts/python/` (invoked by the skills, not directly) resolves paths like `FEATURE_DIR`/`IMPL_PLAN` and copies the right template. Don't hand-edit the numbering scheme or bypass these skills to create feature directories.

### Which tier is the change? (no code before an artifact, then a failing test, then the minimal fix)

| Change | Artifacts | Where |
|---|---|---|
| New behavior or feature | Full chain: specify → plan → tasks → analyze → implement | New `specs/NNN-name/` |
| Bug fix: code contradicts an existing spec or contract | Failing reproduction test, then fix; add a `[x]` task or Amendments line; correct any wrong contract text | Owning spec dir |
| Bug fix: spec silent or wrong | Amend `spec.md` first (FR plus acceptance scenario), then test, fix, update plan and contracts | Owning spec dir |
| Fix that changes behavior or a contract (new route, status code, setting) | Treat as a feature | New spec dir |
| Chore with no behavior change (refactor, deps, CI, docs, assets) | One line in the owning `tasks.md` or an Amendments note; tests stay green | Owning spec dir |

Update contracts and this file in the same PR when the behavior they describe changes. One PR per spec or fix. Run `/speckit-converge` after any ad hoc change. When checking route coverage, walk each router's `.router.routes`; the app's own `.routes` are wrapped and look empty.

## Constitution (binding on all code in this repo)

`.specify/memory/constitution.md` (currently v1.3.0) is the authoritative governance document — `/speckit-plan`, `/speckit-tasks`, and `/speckit-implement` all read it, and code review is expected to enforce it. Key points future work must not violate:

- **Fixed tech stack**: FastAPI (web/API) + HTMX (server-rendered fragments, no SPA framework/build pipeline) + Jinja2 (templates) + SQLite. Diversifying this (second templating engine, frontend framework, alternate DB) requires a constitution amendment, not a unilateral choice in a feature branch.
- **Fixed directory layout**: `app/routers/` (route handlers only, no business logic or direct DB queries), `app/services/` (business logic, must be importable/callable without FastAPI or request objects), `app/models/` (Pydantic schemas + row models), `app/db/` (connection setup, parameterized query functions, migrations — no ORM), `app/templates/`, `app/static/`; `tests/` mirrors `app/` 1:1 (e.g. `tests/services/test_x.py` tests `app/services/x.py`). A file must live in the directory matching its *responsibility*, regardless of what it's named.
- **TDD is non-negotiable**: every behavior change needs a failing test first, then the minimal code to pass. No PR merges with untested new behavior.
- **Security by default**: all input validated at the boundary via Pydantic; all DB access parameterized (no string-built SQL); secrets only from environment config; auth/authz enforced server-side on every route, including HTMX partial endpoints.
- **Observability**: log lines must be human-readable sentences or key=value pairs with relevant IDs, correctly leveled, never containing secrets or full sensitive request bodies.
- **Git practices**: `main` always deployable; short-lived feature branches merged via PR; atomic, imperative-mood commits; no force-push or history rewriting on shared branches.

## Architecture (per plan.md / research.md / data-model.md for 001-bike-maintenance-tracker)

This is a **single-user, self-hosted** app (one rider, one Strava account) — do not add multi-tenancy, auth beyond Strava OAuth, or concurrency handling beyond what a single user needs.

- **Auth**: Strava OAuth2 is the *only* login (no password). Server-side session cookie (Starlette `SessionMiddleware`) after the OAuth callback; tokens live only in the `account` table, never sent to the browser.
- **Data layer**: raw `sqlite3` with hand-written parameterized query functions per entity in `app/db/`, no ORM; schema changes via sequential `.sql` files in `app/db/migrations/` tracked by a `schema_version` table.
- **Component hierarchy**: components form an arbitrary-depth tree (bike → wheel → rim → tire, etc.) via a self-referential adjacency list (`parent_bike_id` / `parent_component_id`), read with recursive CTEs. A small hardcoded "multi-instance type" list (e.g. spoke, bolt, pad) is the only exception to "one component per type per parent" — this deliberately avoids a generic slot/cardinality rules engine.
- **Mileage attribution**: `component_installation_period` rows record when a component was under which parent, so a scheduled Strava sync can attribute historical ride mileage correctly even after components move between bikes.
- **Strava sync**: in-process APScheduler jobs poll Strava's activity API on an interval (deliberately *not* Strava's Webhook Events API — see research.md §1 for why polling was chosen for this single-user scale). The same sync function backs both the scheduled job and the manual `/sync/strava` route.
- **Maintenance due-date projection**: computed on read (never stored) from a trailing riding-pace window plus each schedule's mileage/time interval — see research.md §4 for the exact algorithm and low-confidence fallback rules.
- **Notification dedup**: each `maintenance_schedule` has a `cycle_number` bumped on every completion; `notification` rows are uniquely keyed on `(schedule_id, cycle_number)` to prevent duplicate due-soon alerts within the same cycle.
- **Outbound webhook**: due-soon notifications POST a JSON payload (contract in `contracts/webhook-payload.md`) to a user-configured URL (e.g. a Discord incoming webhook) via `httpx`, with a short timeout and limited retries that never block recording the in-app notification.

**UI**: server-rendered Jinja2 + HTMX, styled only by `app/static/styles.css` (design tokens, automatic light/dark; no framework or build step, per constitution v1.3.0). Reusable macros live in `app/templates/partials/` (icons, forms, badges); the class and markup contract is in `specs/002-modern-ui/contracts/ui-contract.md`. `tests/test_ui_contrast.py` enforces WCAG contrast from the tokens. The Cockpit theme (feature 003) added self-hosted fonts in `app/static/fonts/`, the amber accent, and the "What needs attention" board (`specs/003-cockpit-theme/contracts/ui-contract.md`); urgent/overflow logic lives in `schedule_service.split_attention`. Features 004/005 added the unified bike and part screen: bikes are described by year/make/model/category (`bike_service.create_bike_from_details`), and the part vocabulary is in `app/models/component_kinds.py` (single source of truth: display names and the five palette categories; older kinds are hidden, not removed). Feature 020 removed the placement rules and the one-per-kind limit (any part goes on any part or the bike; only "not inside itself or its own sub-tree" remains) and made the palette a set of collapsible categories (`details.palette-category`, all closed on load; feature 033 renamed the panel "Add a part" and made storage its last section, `details.palette-category.storage-drop.drop-target[data-ref="storage"]`, "In storage (N)"), and `builder_service` builds a scoped view for a root (`bike:ID` or `component:ID`) used by `GET /bikes/{id}` and `GET /components/{id}`, with actions at `/builder/add|move|delete` (`app/routers/builder.py`, shared rendering in `app/routers/screen.py`, drag and drop in `app/static/builder.js`; vanilla JS is allowed only as that small static asset).

Consult `contracts/routes.md` for the full intended HTTP surface (page routes vs. HTMX partial-returning mutation routes) before adding or renaming a route.

## Codex config detected

A Codex CLI config was found at `~/.codex/config.toml`. If you want to import any of it (MCP servers, slash commands, subagents, skills, instructions) into Claude Code, run `/import` to see what's importable, then `/import --yes=<digest>` to apply it.

Bike delete (feature 029): only on the bike's Edit screen, behind a typed-name confirmation: `POST /bikes/{id}/delete` needs `confirm_name` equal to the bike's name exactly (`bike_service.delete_bike_with_name`, `confirmation_service.phrase_matches`); the field's `pattern` comes from `confirmation_service.html_pattern` (escape syntax characters only) and `.delete-confirm:has(input:invalid)` greys the button, so there is no script.

Sync dot (003 FR-006b): `sync_status_service.sync_state` (`ok` / `error` / `off` / `unknown`; error = stale connection or no successful sync for two intervals, using the saved interval else the server default) drives `.sync-status.sync-<state>` and its tooltip; neon green and bright red are the theme-independent tokens `--sync-ok` and `--sync-error`. Since 084 the top bar shows only the dot: its `title` and `aria-label` are `sync_status_service.sync_hover()` ("Sync is working · 7 min ago"), and the Strava connection card shows `sync_line()` ("Sync is working. Last synced 7 minutes ago (...)." per state) beside its own dot. Sign out is an icon-only `btn btn-icon`, and the nav link reads "Maintenance".

Last-sync indicator (003 FR-006a): the top-bar label reads `account.strava_last_synced_at`, set by every successful sync run (`accounts_db.mark_synced` in `sync_incremental` and `backfill_bike`; not on failure or a stale-connection skip), falling back to the newest ride sync time until one is recorded. Since 084 it's shown in the dot's hover text and on the Settings Strava card, not as top-bar text.

Ride log (feature 006 M3): rides live in `ride_activity` (source `strava`|`manual`, `user_modified`, `deleted_by_user`); Strava upserts never overwrite a user-modified or user-deleted ride; `ride_service` owns CRUD and recomputes bike and part mileage. Since 083 the Rides lists show Title (`activity_name`: Strava's title, or a manual ride's, pre-filled "Manual Ride"; a Strava ride's note in `small.ride-note` under it) and Activity type (`sync_rules.sport_label`, Jinja filter `sport_label`; "Manual" for manual rides) instead of Source and Note. Strava titles and types are read-only in the app; migration 0023 moved manual notes into titles; Re-import fills a missing title or type on an edited ride.

Strava pairing (feature 017): the sign-in scope is `profile:read_all,activity:read_all`; paired bikes offer re-import and unpair (`bike_service`); `strava_client` raises `StravaUnavailableError` and `StravaGearAccessError` so routers never see `httpx`.

Settings (feature 023): the account holds the automatic Strava sync switch, its interval (`settings_service.set_sync_settings` applies it to the running scheduler via `scheduler.apply_sync_settings`; `STRAVA_SYNC_INTERVAL_MINUTES` is only the first-run default) and a time zone, picked from a short list such as `(GMT-5) America/New York (EST)` (`clock_service.timezone_choices`: standard offset, prominent city, abbreviation; each entry is a real IANA zone so daylight saving stays correct). Since 075 the zone is not display only: typed times are read in it and stored in UTC, and `clock_service.format_utc` (Jinja filter `local_time`) shows every stored time in it; `localtime.js` was removed. Zone data comes from the `tzdata` dependency.

Maintenance history is service-only (feature 022): adding, moving, removing or deleting a part writes no maintenance entry (migration 0010 deleted the old `kind = 'event'` rows); installs and removals are recorded only as installation periods, shown on a part's Install History and on a bike's (`/bikes/{id}/install-history`, `component_history_service.describe_bike_history`); both can log, edit and delete periods (the bike's edit links carry `?from_bike=ID` so they return there), and logged maintenance entries stay editable.

Still-installed period place (015 FR-014, branch 078): saving a still-installed period with a different Bike or Inside part moves the part there as of its install moment (no new period; `component_history_service._place_open_period`); parts inside it keep their own install moments and follow it, and the recorded bike is the one the part is really on (an Inside part's top bike, none in storage).

Install history cleanup (feature 030): editing a still-installed period with a removed moment ends the installation (`component_history_service.update_period` -> `component_service.move_component(moved_at=...)`, then mileage is recomputed; no maintenance entry); rows of deleted parts read "(deleted)" and can be deleted by hand; deleting a part always asks first (`/builder/delete` and `/components/{id}/delete`, confirmation with a Keep install history checkbox) and deletes the part's own periods unless kept (`component_service.delete_component(keep_history=...)`), while its sub-parts keep theirs.

Install history (feature 015): `component_history_service` owns install dates (`moment`, `installed_at` on add via `/builder/add`) and manual periods at `/components/{id}/install-history` and `/install-periods/{id}`; periods of one part may not overlap and mileage is recomputed after every change.

Clock (feature 036): `account.clock_format` (`12` default, or `24`; `POST /settings/clock`) controls how every displayed time is written: every stored time through `clock_service.format_utc` (Jinja `local_time`) as `2026-11-13 2:26PM EST` (typed times too, since 075; `wall_time` was removed). Form time pickers are the browser's own.

Ride moving time (feature 039): `ride_activity.moving_time_seconds` (NULL = unknown) is set from Strava `moving_time` on sync and re-import (never overwriting edited rides; a missing value never erases a stored one) and by the optional `h:mm` field on manual rides (`ride_service.parse_duration` / `format_duration`, Jinja filter `duration`); the Rides list shows a Moving time column. Schedules by Hours (feature 040) sum it.

Schedules (feature 040): a schedule has a service type (`app/models/schedule_kinds.py`: Charge, Check, Clean, Lube/Wax, Replace, Service, Topup; the type is its name) and one interval of kind Usage (miles, rides, hours) or Period (years, months, weeks), plus Recurring and Receive notifications flags (`maintenance_schedule.service_type`, `interval_kind/value/unit`, `is_recurring`, `notify`, `baseline_at`; migration 0015 rebuilt the table). Miles and weeks also fill the older `interval_miles`/`interval_days`, which older schedules still use unchanged until the rider opens and saves them (`schedule_service.form_defaults` prefills; the rider picks the service type). Rides and hours count `ride_activity` since `baseline_at` (parts only while installed; hours from feature 039's moving time) and project by the blended pace in that unit (085); not recurring = `complete_schedule` logs the maintenance and ends the schedule; notify off = no notification or webhook. The form shows only the unit list for the chosen kind with CSS `:has` (no script). Since 085 the pace is `schedule_service._pace`: the mean of the bike's 90-day pace and its whole-history pace (`mileage_db.lifetime_ride_stats_for_bike`, `lifetime_usage_for_bike`; hours from the first timed ride), trusted once the bike has 5 rides and 30 days of history (`MIN_RIDES_FOR_CONFIDENCE`, `MIN_HISTORY_DAYS_FOR_CONFIDENCE`).

Maintenance log (feature 042): Log and Edit maintenance take a Service type from the same list as schedules (`MaintenanceLogRequest.service_type`, stored in the existing `description` column); older free-text entries display unchanged and need a type chosen when edited.

New schedules (feature 043, 040 FR-011): a typed schedule counts from the latest maintenance entry of the same service type on that bike or part (its date/time, recorded mileage, rides and hours after it); with none, from when tracking began (all rides, not the starting mileage; a period from the earliest install date, else when it was added). `schedule_service._baseline_for`.

Notifications (feature 045): `account.notifications_muted` (Settings "Mute notifications") makes `notification_service.check_due_schedules` record and send nothing; "Send test notification" (`POST /settings/notifications/test`, `notification_service.send_test`) posts to the saved webhook, works even when muted, and records nothing. Since 086 due soon comes from one rule, `schedule_service.due_trigger` (used by `due_status` and `notification_service.check_due_schedules`): the days lead, or for a usage schedule on a bike the Miles / Rides / Hours lead (`account.lead_miles`, `lead_rides`, `lead_hours`, migration 0024, Settings Lead time card, 0 = off), whichever first; the usage ring then shows what's left.

Schedules follow maintenance (feature 046): logging a maintenance entry (not a schedule's own completion) restarts the owner's active schedules of the same service type whose starting point is earlier (new cycle, `maintenance_service._rebase_matching_schedules`); editing an entry re-bases without a new cycle; usage-based projections are always computed on read.

Component maintenance history (feature 048): a part's history lists its own entries plus those of every currently attached part (`maintenance_service.list_for_component_tree`), latest first, with a Part column ("This part" or a link to the attached part's history); attached parts' rows have no Edit or Delete. A bike's history does the same for the bike and all parts attached to it, recursively, with its own entries reading "This bike" (amended in 050).

Period boundaries (015 FR-013, branch 051; replaced by 075): rides and install periods are compared as plain UTC text; the `ride_wall` and `period_wall` SQL functions are gone (`app/db/frames.py` registers only `part_ride_ok`). Part totals are recomputed at startup.

Period rides (feature 053): each period row on a part's and a bike's Install History has a Rides button to `GET /install-periods/{id}/rides` (`?from_bike=ID` from the bike's list): the read-only rides that count toward that period (`mileage_db.list_rides_for_period`, `ride_service.get_log_for_period`, same clock rule as 015 FR-013), no start row or adjustments; its total equals the period's Miles.

Usage overdue (040 FR-012, branch 054): `Projection.over` is how far past a usage interval a schedule is; the ring shows `314mi late` (also rides, hours) and the other-tasks row `314 mi over`. Every button is a bordered `.btn`; the borderless `.btn-quiet` was removed (055). Urgent cards also have Delete, and ring values of 5+ characters get `n5`..`n8` classes sized from `--ring-size` (055).

Schedules page (feature 056): a bike's or part's actions row has a Schedules button (replacing Add schedule) to `/bikes/{id}/schedules` or `/components/{id}/schedules`: that item's active schedules with Add, Edit and Delete (`schedule_service.list_overview_for_owner`, `interval_text`; `schedules/owner_list.html`). Creating a schedule returns there, and Edit/Delete links carry the fixed flag `?from=owner` to return there; without it they return to Maintenance due (only that flag is honored, never a URL).

Strava actions in Edit (feature 057): Re-import Strava history and Unpair from Strava are on a paired bike's Edit screen (`bikes/form.html`), no longer on its main screen; Pair with Strava stays on the main screen.

Period default bike (feature 058): a part's Log a period form preselects the bike it is installed on (through parent parts), else the bike of its most recent period (`component_history_service.default_bike_id`).

Comma separators (feature 059): displayed mileage uses `format_service` (Jinja filters `num1` one decimal, `num0` whole; `count` for interval counts), never `"%.1f"|format`. Inputs and stored values are unchanged.

Sync rules (feature 060): a bike's or part's Edit screen has a Sync rules section (`partials/sync_rules.html`, routes `POST /bikes|components/{id}/sync-rules` in `app/routers/sync_rules.py`): Sport (checkboxes), Ride type (Default/Race/Workout) and Keywords (matched against the activity name, any one), blank = no filter, all filled filters must match (`app/models/sync_rules.py`). Table `sync_rule` (migration 0017) and ride columns `sport_type`, `ride_type`, `activity_name`, `filtered_out` (stored by sync and Re-import). A bike's rule sets `filtered_out` on its unedited Strava rides (`mileage_db.apply_bike_rule`, run on save and after each sync); every live-ride query adds `filtered_out = 0`. A part's rule is applied per call by the SQL function `part_ride_ok` (`app/db/frames.py`) in the part-mileage queries only. Manual and edited rides, and rides with unknown details, always match. Saving re-applies to all existing rides (`sync_rule_service.save_rule`).

Overdue notifications (feature 061): an overdue webhook message ends with `(106d late)` / `(27mi late)` (`notification_service._late`, same rule as `partials/ring.html`); due-soon keeps the remaining text; the payload gains `overdue_amount` and `overdue_unit`.

Sync rules on Add forms (feature 062): `/bikes/new` and `/components/new` include the rule fields (`partials/sync_rules.html` macro `sync_rules_fields`); the create routes validate first (`sync_rule_service.validate_rule`, refusal = 422, nothing created) and save a non-empty rule after creating. Palette-added parts start with no rule.

Inside part picker (feature 063): a part's Log/Edit period form chooses "Inside part" from a list (`component_history_service.parent_options`; a deleted current parent stays listed as "(deleted)"), never a part number.

Nested part mileage (feature 064): `app/db/mileage._WINDOWS` expands every period into (bike, start, end) wall-clock windows; a period inside a part (no bike of its own, which Log/Edit period now stores whenever Inside part is chosen) takes the overlap with the parent's windows, recursively. All part ride sums and lists (total, period Miles, Rides, mileage-at, usage) use it, counting each ride once; period changes call `recompute_all_component_totals`. Older periods that stored a bike keep counting that bike until edited and saved.

Drivetrain part (feature 065): the `drivetrain` kind moved from legacy to the offered Drivetrain category (35 offered kinds).

Maintenance history past parts (feature 066): `maintenance_service.list_for_bike_rows` / `list_for_component_tree` also include entries made while a part was attached (`maintenance_db.list_past_for_bike` / `list_past_for_component`, install-period windows, recursive), once each; deleted parts read "(deleted)".

Backup and restore (feature 067): Settings "Backup and restore" downloads `GET /settings/backup` (a JSON file of every data table plus non-secret account settings, schema-driven by `backup_service`) and restores with `POST /settings/restore` (multipart file plus a required confirm box; all or nothing, ids kept, foreign keys checked, totals recomputed). Strava tokens, athlete id and the webhook URL are never exported or overwritten. A new table needs adding to `backup_service.TABLES`. Files are format 2 since 075; a format-1 file is converted on restore with its own saved zone (`typed_times.convert`).

Rolling backups (feature 068): `BACKUP_DIR` (off when unset), `BACKUP_KEEP` (default 7) and `BACKUP_INTERVAL_HOURS` (default 24) drive a scheduler job `rolling_backup` (`backup_service.write_rolling_backup`: temp file, atomic rename, prune only names matching `bikemaint-backup-*.json`); Settings shows the folder and files and `POST /settings/backup/run` backs up now. Download names are dated in the saved zone (`backup_filename`).

Part icon pack (feature 069): `partials/icons.html` `part(type, class)` draws one approved icon per kind from a data table (styles line, thin, solid-N; markup in `specs/069-part-icon-pack/contracts/icons.md`); rim and spoke show the wheel, unknown kinds the wrench. Redesigns go through the rider first.

Nav icons (feature 070): Maintenance (labelled "Maintenance due" until 084) uses the specs/069 wrench (`wrench()`), Settings a 6-tooth outlined gear (`settings()`).

UI consistency (feature 071): shared layout rules in `styles.css` (section "specs/071": natural-width buttons, value-sized fields, `.card-grid` equal-height cards, `.field-row`, `.check-grid`). Settings is a grid of card templates (`settings/cards/*.html`, macros in `settings/_card.html`) that auto-save via HTMX: routes answer `HX-Request` with `settings/card.html` (one card, "Saved" or "Not saved", always 200), theme adds `HX-Refresh`; other forms keep Save buttons. Bike and part Edit/Add are one form (Details + Sync rules cards, one Save): `POST /bikes/{id}` and `/components/{id}` save the rule when the form carries the hidden `sync_rules` marker (`sync_rules.save_edit_rule`). Row Rides/Edit/Delete are icon buttons (`ui_icons.route/edit/trash`, `aria-label` + `title`).

Due row actions (feature 072): "Everything else" rows have Mark done (circle check, `ui_icons.check_circle`), Edit and Delete as one evenly spaced `.other-actions` group of icon buttons; urgent cards' Mark done is natural width with Edit and Delete at the right edge (072 FR-002, branch 082).

Builder drag and collapse (feature 073): while dragging, the part lifts out (`is-lifted`) and a gap `li.drop-slot` ("on <holder>") opens where it lands; rows glide (FLIP, Web Animations, on even with Reduce Motion); zones top 30% above / bottom 30% below a leaf / else inside (first sub-part when its sub-parts show), sticky by 12%, measured from settled boxes. Rows with sub-parts render `button.twisty` + `.sub-count` (`BuilderNode.descendant_count`), leaves `span.twisty-space`; collapsed ids live in `localStorage["bikemaint.collapsed"]` (try/catch, reapplied after every swap); hovering inside a collapsed part 0.7 s opens it. Same `/builder/add|move` requests. `builder.js` budget is 16 KB.

Zone labels (feature 074): Settings time zone entries show the offset and abbreviation in force when the page is shown (`clock_service.timezone_choices(current, at=None)`, `offset_minutes(name, at)`, default moment `_utc_now()`), ordered by that offset (ties: London first, then name); New York reads `(GMT-4) ... (EDT)` in summer. Tests pin the moment.

Typed times in UTC (feature 075): every stored time is UTC text `YYYY-MM-DDTHH:MM:SS.ffffffZ` (`frames.STORED_FORMAT`). Typed times are read in the saved zone (`frames.to_utc`, `fold=0`; `clock_service.to_utc`; ride blank = noon, install blank = 00:00) and shown with `local_time`; forms prefill with `to_local`, and an unchanged date and minute keep the stored instant (`clock_service.keep_or_convert` / `keep_if_same`). Maintenance entries keep their local `performed_at`/`performed_time` for display, order and date-based schedules and add `performed_instant` (migration 0018; untimed = end of the local day, `frames.end_of_day_utc`) for comparisons (`maintenance_service.entry_moment`, `instant_for`); saving a zone runs `maintenance_service.follow_zone`. Existing data was converted once by the data step `0019_typed_times_utc` (`connection.DATA_STEPS`, `app/db/typed_times.py`, recorded in `schema_version`, one transaction) after a copy beside the database (`<stem>-before-075-<date><suffix>`); data steps run only with the full migrations folder. "Today" is `clock_service.today()` (saved zone) for due dates, notifications and Mark done. See `specs/075-typed-times-utc/contracts/stored-times.md`.

Four-digit years (feature 076): typed dates go through `app/models/typed_dates.full_year` (a `before` validator on every date field, and `form_errors` values): a year from 0 to 99 means 20yy (the browser sends `0026` for a typed 26), and 100 to 1899 is refused with "Enter a valid date". The bike's model Year reads 0 to 99 as 20yy too. Stored instants are written by `frames.stored` with a zero-padded four-digit year (glibc `strftime("%Y")` doesn't pad). Stored short years are repaired by the data step `0020_four_digit_years` (`typed_times.repair_short_years`, re-read in the saved zone, no copy; `DATA_STEPS` entries are `(name, step, copy_first)`) and on every restore. A ride typed by hand can't be in the future (`ride_service.check_not_future`, `clock_service.now()`).

Archive (feature 079): bikes and parts have `archived_at` (migration 0021). `archive_service` archives from the Edit screen (`POST /bikes|components/{id}/archive`, `attached=keep|move`; keep turns off every schedule in the tree, move sends the direct parts to storage with their sub-parts inside and keeps their schedules; a paired bike is unpaired; a part must be in storage) and unarchives from the archived item's Edit screen (`/unarchive`; schedules stay off, the bike stays unpaired). An item is locked when it, a part above it, or its bike is archived (`archive_service.is_locked`, `require_unlocked`, Jinja global `is_locked`); every mutating service calls `require_unlocked`, and `ArchivedError` answers 409 (an app-wide handler, `archived_refusal.html`; builder routes re-render the screen). On a locked item only moving a part to storage, ending its still-installed period, deleting the archived item itself and unarchiving work; `#builder[data-locked]` makes `builder.js` accept only the storage drop. Archived items are left out of every list, picker and Storage count, and shown in a closed `details.archived-section` "Archived (N)" in the Garage and Storage. Strava upserts never touch an archived bike's rides. `tests/routers/test_archive_route_walk.py` fails for any new POST route until it is classified.

Exact miles (feature 081): `sync_service.METERS_PER_MILE = 1609.344`; the data step `0022_exact_miles` (`typed_times.exact_miles`, no copy) rescaled unedited Strava rides once (`source = 'strava' AND user_modified = 0`); manual and edited rides, baselines, adjustments and recorded maintenance mileage keep their typed values. Backups were not reformatted: an older backup restores the old values.
