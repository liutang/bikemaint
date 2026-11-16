# Research: 074 Time Zone Labels Follow the Season

## 1. Which moment a label describes

- **Decision**: the moment the page is shown, in UTC (`datetime.now(timezone.utc)`), converted into each zone. The offset and the zone database's abbreviation (`tzname()`) at that moment make up the label.
- **Rationale**: the rider asked for labels that match "the date of the year". Using one UTC moment for every zone means northern and southern zones each show their own season.
- **Alternatives considered**:
  - The rider's saved zone's local date. This gives the same answer except within hours of midnight, and adds a lookup.
  - Keeping the standard offset (023/027). This is what the rider just asked to change.

## 2. Ordering

- **Decision**: sort by the offset at that same moment. Ties put Europe/London first, then zone name, which is the existing tie rule.
- **Rationale**: if the list were sorted by standard offset but labelled with current offsets, the numbers would read out of order in summer. For example, New York at GMT-4 would sit above Bogotá-style GMT-5 zones. The spec requires offsets to never go down (SC-002).
- **Alternative considered**: a fixed order by standard offset. It was rejected for that reason.

## 3. Testability

- **Decision**:
  - `timezone_choices(current, at=None)` takes an optional moment. Service tests pass 2026-01-15 and 2026-07-15.
  - The default comes from a small `_utc_now()` that route tests replace with a fixed moment.
- **Rationale**: the existing route tests assert EST labels and would otherwise fail every summer.

## 4. Unchanged pieces

- **Kept as they are**:
  - the "no daylight saving" note (Phoenix);
  - dropping brackets when the abbreviation starts with "+" or "-";
  - the off-list "Current: …" entry.

  Only the moment changes.
- **Abbreviation for Azores in July**: the zone database gives `+00`, so it shows no brackets, which is consistent with the existing rule.
