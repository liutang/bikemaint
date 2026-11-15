# Feature Specification: Comma Separators on Mileage

**Feature Branch**: `059-comma-mileage`
**Created**: 2026-11-14
**Input**: User testing feedback: all mileage values should have comma separators.

## User Scenarios & Testing

### User Story 1 - Large Mileages Are Easy to Read (Priority: P1)
**Acceptance Scenarios**:
1. **Given** a total of 12345.6 miles, **Then** every screen that shows it reads `12,345.6 mi`: Garage and Storage cards, bike and part screens, Rides (header total, miles, running totals), Install History miles and total, Maintenance history mileage at service, the Adjust mileage screen, and the new-entry hints.
2. **Given** schedule text, **Then** intervals and remaining or overdue distances use commas too (`Every 1,000 miles`, `1,991 mi over`, the progress ring `1,991mi`, "Next due after 1,500 more miles").
3. **Given** notification text, **Then** "(approx. 1,200 mi remaining)" uses commas.
4. **Given** a value under 1,000, **Then** it reads as before (`548.3 mi`).

## Requirements
- **FR-001**: Displayed mileage MUST use thousands separators, keeping its current number of decimals (one for totals and ride distances, none for remaining/over distances, one for hours).
- **FR-002**: Form fields (number inputs) and stored or JSON values are unchanged: separators are display only.
- **FR-003**: The ring's accessible label MUST use the same separators; its size class is chosen from the displayed text.

## Success Criteria
- **SC-001**: No mileage of 1,000 or more is shown without separators on any screen.

## Assumptions
- Applies the same to ride and hour counts shown in intervals.
