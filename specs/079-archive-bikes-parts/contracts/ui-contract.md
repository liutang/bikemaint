# UI Contract: Archiving (079)

Extends `specs/002-modern-ui/contracts/ui-contract.md`. No script; collapsing uses `<details>`.

| Element | Markup |
|---|---|
| Archived section (Garage, Storage) | `<details class="archived-section">` (closed) > `<summary>Archived (N)</summary>` > `.card-grid` of the usual cards |
| Archived card line | `<p class="archived-on">Archived YYYY-MM-DD</p>` in `bike_row.html` / `storage_card.html` |
| Archive card (active Edit) | `<section class="panel archive-card">` spanning the grid (`grid-column: 1 / -1`) after Strava and Delete; list of effects with real counts; `fieldset.archive-choice` of two radios `attached=keep|move`, none checked, `required` (only when parts are attached); `button.btn` "Archive bike" / "Archive part" |
| Installed part (Edit) | `.archive-card` reads "Take this part off to storage before archiving it." with no button |
| Archived notice | `<p class="archived-notice">` with the archive icon: "Archived YYYY-MM-DD. Its details are locked. Unarchive it below to change them." (Edit) or "...Unarchive it from its Edit screen." (other screens) |
| Read-only details | `<dl class="readonly-details">` in place of the form; no Save |
| Unarchive card | `<section class="panel unarchive-card">` beside Delete; effects list; `button.btn.btn-primary` "Unarchive bike" / "Unarchive part" |

Wording follows the approved mock-ups of 2026-11-18. The Archived sections and the archived bike screen go to the rider as a mock-up before they're built.
