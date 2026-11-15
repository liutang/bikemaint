# Feature Specification: Part Icon Pack

**Feature Branch**: `069-part-icon-pack`
**Created**: 2026-11-15
**Input**: Rider-designed icon pack (review rounds 2026-11-15, approved "build it"): one minimalist icon per part kind so every part is recognizable at a glance; today 11 drawings are shared by 35 kinds.

## User Scenarios & Testing
### User Story 1 - Every Part Has Its Own Icon (Priority: P1)
1. **Given** the palette, builder tree and storage cards, **Then** each of the 35 offered kinds shows its own drawing (no two alike), at the same size and color as today (`icon part-icon`).
2. **Given** older kinds, **Then** `other` and unknown kinds show the wrench, `bolt` has its own bolt, `rim` and `spoke` show the Wheel.
3. **Given** any icon, **Then** it is decorative (`aria-hidden`, `focusable="false"`), always paired with the part's name, and colored by the text color (works in light and dark).

### Edge Cases
- Five icons are solid shapes (Brake Lever, Shift levers, Derailleur, Chainrings, and the Brake's caliper and hub); two use thinner lines (Drivetrain, Wheel Set spokes), as approved.

## Requirements
- **FR-001**: `partials/icons.html` `part(type, class)` MUST render the approved drawing for each kind in `component_kinds` (the approved markup is recorded in `contracts/icons.md`).
- **FR-002**: Offered kinds MUST map to distinct drawings; fallbacks as above.

## Success Criteria
- **SC-001**: The rider can tell any two parts apart by icon alone in the palette.

## Assumptions
- Display only: no data, route or script changes.
