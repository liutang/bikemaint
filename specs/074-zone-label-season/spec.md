# Feature Specification: Time Zone Labels Follow the Season

**Feature Branch**: `074-zone-label-season`
**Created**: 2026-11-16
**Status**: Requested by the rider
**Input**: "I think the numbers and labels should accurately reflect the date of the year and whether or not daylight savings times are active in those time zones." Today every entry in Settings → Time zone shows the zone's standard offset and abbreviation all year: "(GMT-5) America/New York (EST)" even in July (023 FR-006, chosen 2026-11-13 in branch 027). This reverses that choice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The time zone list reads the way clocks read today (Priority: P1)

The rider opens Settings. Each time zone entry shows the offset and abbreviation in force on that day, so in summer New York reads EDT and GMT-4, and in winter EST and GMT-5.

**Why this priority**: It is the whole feature.

**Independent Test**: View Settings on a winter day and on a summer day (or with the date fixed in a test) and compare the entries.

**Acceptance Scenarios**:

1. **Given** a day in July, **Then** the entries include:
   - `(GMT-4) America/New York (EDT)`
   - `(GMT-7) America/Los Angeles (PDT)`
   - `(GMT+1) Europe/London (BST)`
   - `(GMT+2) Europe/Paris (CEST)`
   - `(GMT+10) Australia/Sydney (AEST)`
   - `(GMT+12) Pacific/Auckland (NZST)`
2. **Given** a day in January, **Then** the entries include:
   - `(GMT-5) America/New York (EST)`
   - `(GMT-8) America/Los Angeles (PST)`
   - `(GMT+0) Europe/London (GMT)`
   - `(GMT+1) Europe/Paris (CET)`
   - `(GMT+11) Australia/Sydney (AEDT)`
   - `(GMT+13) Pacific/Auckland (NZDT)`
3. **Given** any day, **Then** zones that never change their clocks read the same:
   - `(GMT-7) America/Phoenix (MST, no daylight saving)`
   - `(GMT+9) Asia/Tokyo (JST)`
   - `(GMT+5:30) Asia/Kolkata (IST)`
   - `(GMT+0) UTC`
4. **Given** a zone with no well-known letter abbreviation, **Then** it shows the offset and city with no brackets, for example `(GMT-3) America/Sao Paulo`.
5. **Given** any day, **Then** the list is ordered by the offset shown, earliest first. Zones may change places when clocks change. When two entries show the same offset, Europe/London comes first, then the others alphabetically.
6. **Given** a saved zone, **Then** the card's "Currently …" line uses the same label as its entry. A saved zone that is not in the list appears as "Current: …" with the same rule.

### Edge Cases

- **The day the clocks change**: the label follows the moment the page is shown. A page loaded just before the change shows the old offset until it is reloaded.
- **Different hemispheres**: northern and southern zones are on summer time in opposite halves of the year. Each entry follows its own zone.
- **Saving**: the value saved is still the zone itself, not an offset, so saving in summer and reading in winter needs no change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each Time zone entry MUST read `(GMT<offset>) <Region/City> (<abbreviation>)`, using the offset and abbreviation in force in that zone at the moment the page is shown. This amends 023 FR-006, which used the standard offset all year.
- **FR-002**: The "no daylight saving" note, the omitted brackets for zones without a letter abbreviation, and the "Current: …" entry for an off-list saved zone MUST stay as they are. Only the offset and abbreviation follow the date.
- **FR-003**: Entries MUST be ordered by the offset shown, earliest first. Ties put Europe/London first, then the rest by zone name.
- **FR-004**: The "Currently …" line MUST match the selected entry's label, without the "Current: " prefix.
- **FR-005**: Nothing stored changes. The saved setting stays a zone name. Displayed times keep using the offset of their own date.

## Success Criteria *(mandatory)*

- **SC-001**: On any day of the year, every entry's offset and abbreviation match what a clock in that zone shows that day.
- **SC-002**: Reading the list top to bottom, the offsets never go down.

## Assumptions

- "The date of the year" means the moment the Settings page is shown, not the date of any ride.
- The set of zones offered does not change.
- The card's hint ("Zones that change their clocks follow daylight saving automatically…") stays accurate and is kept.
