# Feature Specification: Modern UI

**Feature Branch**: `002-modern-ui`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Modernize the look and feel of the Bike Maintenance Tracker web UI without changing any behavior. Replace the current near-unstyled HTML with a cohesive, modern, fast-loading design: a consistent app shell (top bar with navigation to Garage, Maintenance due, Settings, sign out), a design-token based visual system with automatic light and dark mode following the OS preference, responsive layout that works well on a phone, cards for bikes and components, a readable nested component tree with expand/collapse, a clean due-soon dashboard table with clear overdue / due-soon / low-confidence status badges, polished forms with inline validation errors, clear buttons and destructive-action confirmation styling, empty states, and accessible contrast, focus states and semantic markup. Interactions should feel instant using HTMX partial swaps already in the app (e.g. marking a schedule done updates its row in place). Styling is plain CSS served from app/static/ per constitution v1.3.0 (no JS framework, no runtime build step). All existing routes, behavior and the existing automated tests must keep working."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent, Navigable App Shell (Priority: P1)

As the rider, I want every page to share the same recognizable frame — a top bar with the app name, links to Garage, Maintenance due and Settings, and a way to sign out — and a clean, readable page layout, so the app feels like one product and I can reach any area in one click from anywhere.

**Why this priority**: The shell and visual system are the foundation every other page is styled on. Delivering it alone already transforms the first impression of every screen and is independently demonstrable.

**Independent Test**: Visit the sign-in page, the garage, the due-soon dashboard and settings; confirm each shows the same frame, the current section is visibly highlighted, sign-out is reachable, and text is comfortably readable.

**Acceptance Scenarios**:

1. **Given** a signed-in rider on any page, **When** the page loads, **Then** a top bar shows the app name and links to Garage, Maintenance due and Settings, with the current section visibly indicated, plus a sign-out control.
2. **Given** a rider who is not signed in, **When** they open the sign-in page, **Then** it uses the same visual style but shows no navigation to protected areas.
3. **Given** a rider whose device is set to dark mode, **When** any page loads, **Then** it renders in a dark theme automatically (and in a light theme when the device is set to light), with no flash of the wrong theme and no manual switch needed.
4. **Given** a rider on a phone-width screen, **When** they use any page, **Then** the navigation remains reachable, content does not require horizontal scrolling, and tap targets are comfortably sized.

---

### User Story 2 - Garage and Component Views That Are Easy to Scan (Priority: P2)

As the rider, I want my bikes shown as cards (name, type, mileage, and quick actions) and each bike's components shown as a readable nested tree that I can expand and collapse, so I can see my whole build at a glance and drill into a wheel → rim → tire without clutter.

**Why this priority**: The garage and component tree are the most-visited screens and the places where the current unstyled lists are hardest to read. It depends only on the shell from Story 1.

**Independent Test**: With several bikes and a three-level nested component set, open the garage and a bike's detail page; confirm cards, readable nesting, working expand/collapse, mileage shown per item, and helpful empty states for a new garage and for storage.

**Acceptance Scenarios**:

1. **Given** several bikes, **When** the rider opens the garage, **Then** each bike appears as a card showing its name, type and total mileage with clear actions, and components in storage appear in their own clearly labeled section.
2. **Given** a bike with nested components, **When** the rider opens it, **Then** the nesting depth is visually obvious, each item shows its type and mileage, and any branch can be collapsed and expanded without leaving the page.
3. **Given** a brand-new account with no bikes or an empty storage list, **When** the rider opens the garage, **Then** a friendly empty state explains what to do next and offers the primary action.
4. **Given** the rider deletes a bike or component that requires confirmation, **When** the confirmation appears, **Then** it is visually distinct as a destructive action, states what will be deleted, and offers a clear cancel path.

---

### User Story 3 - A Maintenance Dashboard You Can Read at a Glance (Priority: P3)

As the rider, I want the due-soon dashboard to show each upcoming item with a clear status — overdue, due soon, on track, or low-confidence estimate — its projected date and remaining mileage, and I want "Mark done" to update that item right where it is, so I can triage maintenance quickly.

**Why this priority**: This is where the rider decides what to work on; clear status cues have the highest day-to-day payoff after the shell and garage views.

**Independent Test**: With schedules in each state (overdue, inside the lead-time window, comfortably far out, no estimate yet), open the dashboard; confirm each is distinguishable at a glance without relying on color alone, that in-app alerts can be dismissed, and that marking an item done updates only that item without reloading the page.

**Acceptance Scenarios**:

1. **Given** schedules in different states, **When** the dashboard loads, **Then** each row shows a status badge (overdue, due soon, on track, or low confidence) whose meaning is conveyed by text and icon as well as color.
2. **Given** an item on the dashboard, **When** the rider marks it done, **Then** that row updates in place to its new state without a full page reload, and the rest of the page keeps its position.
3. **Given** unacknowledged in-app alerts, **When** the dashboard loads, **Then** they are shown prominently above the list and each can be dismissed individually.
4. **Given** no schedules exist, **When** the dashboard loads, **Then** an empty state explains how to add one from a bike or component.
5. **Given** a phone-width screen, **When** the dashboard loads, **Then** the rows remain readable without horizontal scrolling of the whole page.

---

### User Story 4 - Polished Forms and Feedback (Priority: P4)

As the rider, I want every form (bike, component, move, maintenance entry, schedule, mileage adjustment, pairing, settings) to be tidy and clear, with validation problems shown next to the field they concern, so entering data is quick and mistakes are easy to fix.

**Why this priority**: Forms are used constantly but each one already works; polish improves the experience without blocking the higher-visibility screens above.

**Independent Test**: Submit each form with invalid input; confirm the error appears beside the relevant field (and as a summary), the entered values are kept, labels and hints are clear, and primary versus secondary versus destructive actions are visually distinct.

**Acceptance Scenarios**:

1. **Given** any form, **When** the rider submits invalid input, **Then** the form re-displays with the rider's entries preserved and an error message adjacent to each offending field.
2. **Given** any form, **When** the rider navigates by keyboard, **Then** every control shows a clearly visible focus indicator and the tab order follows the visual order.
3. **Given** a form with both a save action and a destructive action, **When** it is displayed, **Then** the save action is the visually primary button and the destructive action is visually distinct and set apart.

---

### Edge Cases

- A very long bike, component or schedule name must wrap or truncate gracefully rather than breaking the layout.
- A component tree of many levels or many siblings must remain usable on a phone-width screen.
- A rider with the browser set to reduced motion must not see animated transitions.
- A rider who switches the device between light and dark mode while the app is open sees the theme follow without a reload.
- The page must remain fully usable if the enhanced in-place updates fail to load (standard navigation and form posts still work).
- Pages must remain readable with the browser text size increased.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every page MUST share a common frame consisting of a top bar with the app name, navigation to Garage, Maintenance due and Settings (with the current section indicated), and a sign-out control; the sign-in page MUST use the same visual style without the navigation.
- **FR-002**: The application MUST use a single consistent visual system (colors, type scale, spacing, corner radii, shadows) defined once and reused by every page.
- **FR-003**: The application MUST automatically follow the rider's operating-system light or dark preference, including changes made while the app is open, without a manual toggle.
- **FR-004**: All pages MUST be usable on screens from phone width (about 360 px) to wide desktop, with no horizontal page scrolling, readable text, and tap targets of at least 44 px on touch devices.
- **FR-005**: Bikes MUST be presented as cards showing name, type, total mileage and quick actions; components in storage MUST be presented in a clearly labeled, similarly styled section.
- **FR-006**: A bike's or component's nested components MUST be presented as a visually indented tree showing each item's type and mileage, in which any branch can be collapsed and expanded in place.
- **FR-007**: The due-soon dashboard MUST present each schedule with its owner, projected date, remaining mileage and a status badge for overdue, due soon, on track, or low-confidence, where status is conveyed by text or icon in addition to color.
- **FR-008**: Marking a schedule done, dismissing an in-app alert, and confirming a delete MUST update the affected part of the page in place wherever the application already supports partial updates, falling back to normal navigation when they are unavailable.
- **FR-009**: Every form MUST show validation errors beside the field concerned (plus a summary), preserve the rider's entries on error, and visually distinguish primary, secondary and destructive actions.
- **FR-010**: Destructive confirmations MUST state what will be deleted, be visually distinct as destructive, and offer an obvious way to cancel.
- **FR-011**: Pages with no data (no bikes, empty storage, no schedules, no maintenance history, no alerts) MUST show an informative empty state with the next action.
- **FR-012**: The UI MUST meet WCAG 2.1 AA expectations for text contrast in both light and dark themes, MUST show a visible focus indicator on every interactive element, and MUST use semantic page structure (landmarks, headings, labelled form controls, table headers) so assistive technology can navigate it.
- **FR-013**: The UI MUST respect the rider's reduced-motion preference by omitting non-essential animation.
- **FR-014**: This feature MUST NOT change any route, form field, stored data, calculation, notification or other behavior; every existing automated test MUST continue to pass unchanged in meaning.
- **FR-015**: Styling MUST add no new client-side framework and no step required to run or deploy the application, consistent with the project constitution.

### Key Entities

This feature changes presentation only and introduces no new data entities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a first load over a typical home broadband connection, every page becomes fully styled and usable in under 1 second, with the total styling and script assets for any page under 150 KB.
- **SC-002**: A rider can reach Garage, Maintenance due and Settings from any page in a single click or tap.
- **SC-003**: Every page is fully usable at 360 px width with zero horizontal page scrolling.
- **SC-004**: Text and interactive-element contrast meets WCAG 2.1 AA in both light and dark themes on every page, verified by an automated accessibility check with no critical violations.
- **SC-005**: A rider can identify which maintenance items are overdue within 5 seconds of opening the dashboard, without relying on color perception.
- **SC-006**: Marking a schedule done updates the dashboard row with no full-page reload.
- **SC-007**: The existing automated test suite passes with no behavioral test changes, and no stored data, route or form field changes.

## Assumptions

- The theme follows the operating-system preference only; a manual light/dark toggle is out of scope.
- Supported browsers are current evergreen desktop and mobile browsers (latest two major versions of Chrome, Safari, Firefox and Edge).
- Nested component branches are expanded by default and can be collapsed; the collapsed state is not remembered between visits.
- No logo or brand artwork exists yet; the app name appears as text, with an optional simple icon.
- Icons are simple inline graphics or text symbols rather than an external icon service, so the app works offline from the rider's own server.
- Per project constitution v1.3.0, styling is plain CSS (hand-written or vendored) served from the application's static assets, with no JavaScript framework and no build step required to run or deploy.
- Existing partial-update behavior (for example marking a schedule done) is reused; new server routes are not required for this feature.
