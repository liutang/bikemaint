# Feature Specification: Navigation Icons

**Feature Branch**: `070-nav-icons`
**Created**: 2026-11-15
**Input**: User testing feedback: the Maintenance due nav icon should be the wrench (the squashed one read as a pen); the Settings icon should be a standard gear (the old one looked like a sun). Rider chose gear B (6 teeth) from samples.

## User Scenarios & Testing
### User Story 1 - Recognizable Nav Icons (Priority: P1)
1. **Given** the top bar, **Then** Maintenance due shows the same wrench as the "Other part" icon (specs/069) and Settings shows a 6-tooth outlined gear with a round hole.
2. **Given** either icon, **Then** it stays decorative, outlined (stroke 2, currentColor) and paired with its label.

## Requirements
- **FR-001**: `icons.html` `wrench()` MUST draw the specs/069 wrench; `settings()` MUST draw the 6-tooth gear (path in plan.md).

## Success Criteria
- **SC-001**: The rider recognizes both nav icons without reading the labels.

## Assumptions
- Display only.

## Amendments

- **2026-11-18 (feature 084)**: the wrench link's label is "Maintenance" (was "Maintenance due"); the icon is unchanged. See `specs/084-quiet-top-bar/`.
