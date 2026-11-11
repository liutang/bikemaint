# Data Model: Bike Catalog and Interactive Builder

## Schema changes

| Migration | Change |
|-----------|--------|
| `0005_bike_catalog_id.sql` (M1) | `ALTER TABLE bike ADD COLUMN catalog_id TEXT` (NULL = legacy bike) |
| `0006_component_position.sql` (M3) | `ALTER TABLE component ADD COLUMN position INTEGER NOT NULL DEFAULT 0`; backfill `position` as the row's order among siblings by `id` |

## Reference data (code, not tables)

- **BikeCatalogEntry**: `id` (slug), `make`, `model`, `category` ∈ {road, gravel, mountain, hybrid, e-bike}. Display name = `"{make} {model}"`; `bike_type` stored on the bike = category.
- **ComponentKind**: `type`, `label`, `allowed_parents` (subset of {"bike"} ∪ component types), `multi_instance` (existing `MULTI_INSTANCE_COMPONENT_TYPES`), `palette` (shown in the builder palette).

## Allowed parents (default catalog)

| Type | Parents | Multi |
|------|---------|-------|
| frame, fork, wheel, drivetrain, brake, handlebar, stem, seatpost, saddle | bike | no |
| hub, rim | wheel | no |
| spoke | wheel | yes |
| tire | rim | no |
| cassette, rotor | hub | no |
| crankset, chain, derailleur | bike, drivetrain | no |
| pedal | crankset | yes (left/right) |
| shifter | bike, handlebar | yes |
| pad | brake, bike | yes |
| bolt, other | any | yes |

Storage (no parent) is always allowed for every type.

## Invariants
- Rules apply to new creates and moves; existing rows are never rewritten.
- A component is never moved under itself or its own sub-tree (existing rule).
- Sibling positions are unique per parent after any reorder (renumbered 0..n).
