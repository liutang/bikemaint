# UI Contract: 084 Quiet Top Bar (amends 002's header and 003 FR-006a/b presentation)

| Element | Markup |
|---|---|
| Maintenance link | `<a href="/maintenance/due" …>{{ ui_icons.wrench() }}Maintenance</a>` |
| Sync status | `<span class="sync-status sync-<state>" role="img" title="HOVER" aria-label="HOVER"></span>`, with no text content; HOVER is for example "Sync is working · 7 min ago" |
| Sign out | `<button class="btn btn-icon" type="submit" aria-label="Sign out" title="Sign out">{{ ui_icons.sign_out() }}</button>` |
| Strava card line | `<p class="sync-line"><span class="sync-status sync-<state>" aria-hidden="true"></span>SENTENCE</p>` below "Connected since…" |
| Mute card | "… Schedules still appear under Maintenance." |
