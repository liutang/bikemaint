# Implementation Plan: Quiet Top Bar

**Branch**: `084-quiet-top-bar` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

These are template, style and wording changes, plus one new service function:
- **`layout.html`:**
  - The nav label reads "Maintenance".
  - `.sync-status` renders only the dot, with `title` and `aria-label` from a new `sync_status_service.sync_hover()`, for example "Sync is working · 7 min ago".
  - Sign out becomes `btn btn-icon` with `aria-label="Sign out"` and `title="Sign out"`.
- **`settings/cards/strava.html`** gets a last-sync line from a new `sync_status_service.settings_line()`, which returns the state, the relative time and the local time, with a matching dot.
- **`settings/cards/mute.html`** wording changes.
- **CSS:** the sync dot loses its text spacing, and on phones no longer takes a full row.

Markup is in [contracts/ui-contract.md](contracts/ui-contract.md).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: none new
**Storage**: none
**Testing**: pytest.
- `sync_status_service` text for every state and age, with a pinned `now`.
- Header markup, the card line and the Mute wording, through route tests.

**Constraints**:
- no script;
- every control keeps an accessible name;
- 003 FR-006b colours and states are unchanged.

**Scale/Scope**: 1 service, 3 templates, styles, tests, and amendments to 002, 003, 045, 070 and CLAUDE.md.

## Constitution Check

- **Fixed stack and no script**: PASS.
- **Layout**: wording logic in `app/services/sync_status_service.py` (testable without a request), and markup in templates. PASS
- **III. TDD**: failing tests first. PASS
- **IV/V**: no new input, no new logs. PASS
- **Git**: one branch, one PR. PASS

## Design

- **`sync_hover(state, synced_at, now)`:**
  - `"<state words> · <relative>"`, where the state words are "Sync is working", "Sync isn't working", "Automatic sync is off" or "Sync status unknown".
  - The relative part reuses `format_label`'s buckets without "Synced": "just now", "7 min ago", "3 h ago", "2 d ago".
  - With no sync yet, it reads "<state words> · Not synced yet".
- **`settings_line(state, synced_at, now)`** gives the spec's four sentences, with the relative time in full words ("7 minutes ago", "3 hours ago", "2 days ago") and the local time through `clock_service.format_utc`.
- **Phone layout:** the 40rem rule that gave `.sync-status` `flex-basis: 100%` is removed, so the dot sits in the bar's flow.

## Project Structure

```text
app/services/sync_status_service.py   sync_hover(), settings_line()
app/templates/layout.html             label, dot-only sync status, icon-only Sign out
app/templates/settings/cards/strava.html, settings/cards/mute.html
app/static/styles.css                 .sync-status without text; phone rule removed
tests/services/test_sync_status_service.py, tests/routers/test_layout*.py or test_ui_pages.py, tests/routers/test_settings.py
```

## Complexity Tracking

None.
