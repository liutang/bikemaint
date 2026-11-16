# Feature Specification: Consistent, Compact, Responsive Layout

**Feature Branch**: `071-ui-consistency`
**Created**: 2026-11-15
**Input**: Rider review of mock-ups (2026-11-15, approved "build it"): buttons stretch across the page on Settings; cards leave uneven gaps; bike and part Edit have two Save buttons; Settings should auto-save; row actions should be icons. The layout must be consistent across tabs and display cleanly on phones, tablets and desktops (rider's usual browser is about 1,200px wide).

## User Scenarios & Testing

### User Story 1 - Natural-width buttons and right-sized fields everywhere (P1)
1. **Given** any form, **Then** a button sits at its natural width, left-aligned; never a full-width bar.
2. **Given** number, date and time fields and drop-downs, **Then** they are sized to their values; text fields (names, URLs, keywords) stay full width.
3. **Given** a phone (375px), tablet (768px) or desktop (1,200px) width, **Then** no page scrolls sideways.
4. **Given** a card, **Then** its main action is orange; secondary actions beside it are white.

### User Story 2 - Settings as aligned cards that save themselves (P1)
1. **Given** Settings at desktop width, **Then** cards sit in two columns; cards in a row share one height; Webhook and Automatic backups span both columns; one column on tablets and phones.
2. **Given** a change to a setting (theme, sync on/off and interval, webhook URL, mute, lead time, time zone, clock), **Then** that card saves itself (choices at once, text and numbers when leaving the field or pressing Enter) and shows "Saved", or "Not saved" with the reason beside the field, keeping the stored value. No Save buttons remain; with scripting off, a Save button appears in each card.
3. **Given** the Webhook card, **Then** the description no longer repeats the URL, and Send test notification is its button.
4. **Given** backups, **Then** there are three cards: Backup (Download backup), Restore (file, confirm box, Restore backup), and Automatic backups (folder, interval, how many kept, recent files with their age, Back up now) or a note on how to turn them on.

### User Story 3 - One Save on bike and part Edit (P1)
1. **Given** a bike's or part's Edit (and Add) screen, **Then** Details and Sync rules are two cards in one form with a single Save and Cancel; saving stores the details and the sync rule together (an empty rule removes it); a refused save changes nothing and keeps what was typed.
2. **Given** a paired bike, **Then** the Strava card (Re-import, Unpair) sits beside the Delete card below the form.
3. **Given** the part screens, **Then** the browser tab reads "Edit part" / "Add part".

### User Story 4 - Icon buttons for row actions (P2)
1. **Given** rows on Install History (part and bike), Rides, Maintenance history, a Schedules page and Maintenance due, **Then** Rides, Edit and Delete are square icon buttons (route, pencil, trash) with a tooltip and an accessible name; the top action bars of bike and part screens keep their text buttons.

## Requirements
- **FR-001**: Shared CSS rules implement US1 for every page (no per-page exceptions).
- **FR-002**: Settings routes answer an HTMX request with the re-rendered card (status "Saved" or "Not saved"); non-HTMX requests behave as before.
- **FR-003**: `POST /bikes/{id}` and `POST /components/{id}` also take `sport`, `ride_type`, `keywords` and save the rule; the separate sync-rule routes stay for compatibility but are no longer linked.
- **FR-004**: No new client-side script: auto-save uses HTMX attributes only.

## Success Criteria
- **SC-001**: Settings at 1,200px is about half its previous length, with no full-width buttons.
- **SC-002**: No page scrolls sideways at 375px.

## Assumptions
- Add forms and the other edit forms keep their Save buttons (rider: auto-save on Settings only).
