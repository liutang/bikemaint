# Research: 020 Free Placement and Categorised Palette

## 1. Removing the rules versus making them configurable

- **Decision**: Delete the placement rules and the one-per-kind limit outright.
- **Rationale**: The rider wants no restriction and will act as the mechanic. A configurable rules engine was rejected in the 001 architecture and would be needless for one user (constitution I).
- **Alternatives**: A "strict/free" toggle (extra state, two code paths); keeping rules as warnings only (still noise the rider asked to remove).

## 2. What validation remains

- **Decision**: Only "a part cannot be placed under itself or inside its own sub-tree" (moves) and "type must be an offered kind" (creation). Both are enforced server-side; the drag script mirrors the first for feedback only.
- **Rationale**: Cycles would corrupt the tree and break recursive reads; everything else is the rider's choice.

## 3. Collapsible categories without JavaScript

- **Decision**: One native `<details>` per category inside the palette, none with `open`; no state saved.
- **Rationale**: Built-in keyboard and screen-reader behavior, several open at once, zero script, matches "Simplicity" and the "vanilla JS only as builder.js" rule.
- **Alternatives**: Accordion script (more code, single-open by default behavior); persisting state in localStorage (rider did not ask; adds a stale-state surface).
- **Risk**: Drag from a collapsed section is impossible by design; dragging from an open one works because items remain `draggable` elements.

## 4. Existing kinds and the supplied list

- **Decision**: Reuse an existing type id when the names match; map `pedal`, `shifter`, `pad` to "Pedals", "Shift levers", "Brake Pads"; add 16 new ids; keep `drivetrain`, `other`, `rim`, `spoke`, `bolt` as legacy (valid, hidden).
- **Rationale**: No data migration; existing parts keep their ids and simply display the catalog name.
- **Alternatives**: Rename ids in the database (needless migration and risk).
- **Note**: "Wheel" and "Wheel Set" stay separate kinds; "Accessories" is both a category and a kind, as supplied.

## 5. Icons

- **Decision**: New kinds fall back to the existing wrench icon; a few map to the nearest existing drawing (brake_lever and brake_cable → brake, bottom_bracket and chainrings → drivetrain, shifter_cable → chain, axle/tube → wheel/tire).
- **Rationale**: Feature 006 requires recognizable icons for the part kinds it listed; new kinds are outside that list, so a fallback is acceptable and can be improved later.

## 6. Display names

- **Decision**: A catalog `name` per kind, exposed to templates through a `kind_name` filter, replaces printing the raw type id on chips and the detail page.
- **Rationale**: "Shift levers" reads better than `shifter`; needed so existing parts show the palette name (spec edge case).
