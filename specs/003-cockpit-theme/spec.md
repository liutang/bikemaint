# Feature Specification: Cockpit Theme

**Feature Branch**: `003-cockpit-theme`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Restyle the Bike Maintenance Tracker UI with the approved 'Cockpit' visual direction, without changing any behavior or routes: softened-charcoal dark theme and cool-grey light theme following the OS preference, a single amber brand accent (#FFA800), a pill-navigation top bar, a 'What needs attention' maintenance page with progress-ring cards (at most six, overflow collapsed into a '+N more tasks' tile) and a compact list of non-urgent items, every other screen restyled to match, WCAG AA contrast in both themes, plain CSS only." Reference mockups: Cockpit dark, light and busy-week artboards in the design canvas at https://claude.ai/artifact/2nxeCbSQ7dhkCyzz5kPWrJ.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cockpit Look and Shell on Every Page (Priority: P1)

As the rider, I want the whole app to share the approved Cockpit look: a softened charcoal dark theme (never near-black) and a cool-grey light theme with white surfaces, switching automatically with my device setting, one amber accent for primary actions and the current page, a top bar with pill-style navigation, and a sync indicator, so the app feels cohesive and polished.

**Why this priority**: The color system, type and shell are the foundation every other screen is built on, and alone they already transform every page.

**Independent Test**: Open the sign-in page, garage, bike detail, maintenance pages and settings in a dark-mode and a light-mode browser; confirm both themes, the amber accent, the pill navigation with the current page highlighted, the sync indicator and sign-out in the top bar.

**Acceptance Scenarios**:

1. **Given** a device set to dark mode, **When** any page loads, **Then** it shows a charcoal (not near-black) page background with slightly lighter raised surfaces and subtle borders, and a device set to light mode shows a cool-grey page with white surfaces.
2. **Given** any signed-in page, **When** it loads, **Then** the top bar shows the logo, pill navigation (Garage, Maintenance due, Settings) with the current page filled in the amber accent, a "synced N minutes ago" indicator, and sign out.
3. **Given** a primary button or the current-page pill, **When** it is displayed in either theme, **Then** it is amber with dark text that remains readable.
4. **Given** light mode, **When** links, the logo mark, or keyboard focus rings are displayed on a white or grey surface, **Then** they use a darker amber shade so they stay clearly visible.
5. **Given** a phone-width screen, **When** any page loads, **Then** the top bar and navigation remain reachable and nothing scrolls horizontally.

---

### User Story 2 - "What Needs Attention" Maintenance Page (Priority: P2)

As the rider, I want the Maintenance due page to lead with what needs action now: urgent tasks as cards with a progress ring showing how late or how close each one is, most urgent first, and everything else in a quiet list below, so I can decide what to work on in seconds even in a busy week.

**Why this priority**: This is the screen where decisions are made, and the ring cards and overflow handling are the centerpiece of the approved design.

**Independent Test**: With schedules in every state, open the page; confirm urgent cards with rings, ordering, the overflow tile when more than six are urgent, the compact list for the rest, in-place "Mark done", and the empty state.

**Acceptance Scenarios**:

1. **Given** overdue and due-soon tasks, **When** the page loads, **Then** each appears as a card with a progress ring, the task name, bike, due date and a Mark done button, titled under "What needs attention".
2. **Given** an overdue task, **When** its card is shown, **Then** its ring is fully filled in red and labelled with how many days late; a due-soon task shows a partial gold arc labelled with days left, the arc growing as the due date nears.
3. **Given** urgent tasks, **When** the page loads, **Then** overdue tasks come before due-soon tasks and, within each, the most overdue or soonest due comes first.
4. **Given** more than six urgent tasks, **When** the page loads, **Then** five cards plus a "+N more tasks" tile are shown (six tiles in total), and choosing View all on that tile shows every urgent task.
5. **Given** two or three urgent tasks, **When** the page loads, **Then** cards use two columns, with three columns when there are more, and a single column on a phone-width screen.
6. **Given** tasks that are on track or have no estimate yet, **When** the page loads, **Then** they appear in a compact list below with a status badge (on track, or low confidence / no estimate) and still offer Mark done.
7. **Given** a card or list row, **When** the rider marks it done, **Then** that item updates in place without a full page reload and the page counts and ordering remain correct.
8. **Given** no tasks are urgent, **When** the page loads, **Then** a friendly "nothing needs attention" state is shown above the list of other tasks; given no schedules exist at all, an empty state explains how to add one.
9. **Given** a ring, **When** it is read by a screen reader or viewed without color, **Then** its meaning ("overdue by 30 days" / "due in 4 days") is available as text and not conveyed by color alone.

---

### User Story 3 - Every Other Screen Matches (Priority: P3)

As the rider, I want the garage, bike detail with its component tree, component pages, maintenance history, forms, settings, sign-in and delete confirmations to adopt the same look, so there is no leftover old styling anywhere.

**Why this priority**: Consistency matters, but each screen already works and is already styled; this is a restyle onto new design tokens.

**Independent Test**: Visit every page in both themes; confirm cards, tree, tables, forms, alerts and confirmations all use the Cockpit surfaces, borders, type and accent, and that existing interactions (expand/collapse, inline delete confirmation, field errors) still work.

**Acceptance Scenarios**:

1. **Given** any page other than the maintenance page, **When** it is shown in either theme, **Then** it uses the same surfaces, borders, corner radii, typography and button styles as the maintenance page.
2. **Given** forms with errors, **When** they are displayed, **Then** errors, focus indicators and the primary, secondary and destructive buttons remain clearly distinguishable in both themes.
3. **Given** status badges anywhere in the app, **When** displayed, **Then** overdue is red, due soon is gold, on track is green and no-estimate/low-confidence is grey, each with an icon and text label, and due-soon gold is visibly different from the amber brand accent.

---

### Edge Cases

- Exactly six urgent tasks show as six cards with no overflow tile; seven show five cards plus "+2 more tasks".
- A task due today is shown as due soon with a label such as "Today", never as "0 days left" or "late".
- A very long task or bike name wraps or truncates gracefully within a card.
- Tasks with no estimate yet (low confidence) never appear among the urgent cards.
- If in-place updates are unavailable, Mark done still works through normal navigation.
- A rider who has never synced with Strava sees "Not synced yet" instead of a time.
- Reduced-motion preference: rings and any transitions are not animated.
- Text size increased in the browser must not break the cards or ring labels.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide a dark theme using a softened charcoal palette (page background lighter than near-black, with raised surfaces and borders one step lighter) and a light theme using a cool grey page with white surfaces, selected automatically from the device preference with no manual toggle.
- **FR-002**: A single brand accent, amber (#FFA800), MUST be used as the fill for primary buttons and the current navigation pill, always with dark text, in both themes.
- **FR-003**: In light mode, text-like uses of the accent (links, logo mark, focus rings) MUST use a darker amber shade that meets contrast requirements on light surfaces.
- **FR-004**: Status colors MUST be distinct from the accent: overdue red, due soon gold, on track green, no estimate / low confidence grey; every status MUST also carry an icon and a text label.
- **FR-005**: Headings and body text MUST use the Cockpit typefaces (a geometric display face for headings, a neutral sans for body) with a sensible system fallback, and the app MUST NOT make runtime requests to external font or style services.
- **FR-006**: Every signed-in page MUST show a top bar with the logo, pill navigation to Garage, Maintenance due and Settings (current page highlighted), a last-sync indicator, and sign out; the sign-in page MUST use the same look without protected navigation.
- **FR-007**: The Maintenance due page MUST be titled "What needs attention" and present urgent tasks (overdue and due soon) as cards ordered overdue-first, then by most overdue or soonest due.
- **FR-008**: Each urgent card MUST show a progress ring, task name, bike or component owner, due date and a Mark done button. An overdue ring MUST be completely filled in red and labelled with days late; a due-soon ring MUST show a gold arc proportional to how close the due date is within the notification lead time, labelled with days left.
- **FR-009**: At most six tiles MUST appear in the urgent area; when more than six tasks are urgent, the first five MUST be cards and the sixth tile MUST be "+N more tasks" with a View all control that reveals every urgent task.
- **FR-010**: The urgent area MUST use two columns for small counts, three columns for larger counts, and one column on phone-width screens.
- **FR-011**: Tasks that are on track or have no estimate MUST appear in a compact list below the urgent area with a status badge and a Mark done control.
- **FR-012**: Marking a task done MUST continue to update that item in place without a full page reload (falling back to normal navigation), with ordering and counts consistent afterwards.
- **FR-013**: When no task is urgent, the page MUST say so positively and still show the other tasks; when no schedules exist, it MUST show an empty state that explains how to add one.
- **FR-014**: Rings MUST expose their meaning as text to assistive technology and MUST NOT rely on color alone.
- **FR-015**: Every other screen (garage, bike detail and component tree, component pages, maintenance history, forms, settings, sign-in, delete confirmations, alerts) MUST be restyled to the same design tokens, preserving existing structure: landmarks, expand/collapse tree, stacked tables on phones, inline confirmations and per-field errors.
- **FR-016**: The UI MUST meet WCAG 2.1 AA text and interactive-element contrast in both themes, checked automatically from the design tokens, and MUST keep a visible focus indicator on every interactive element.
- **FR-017**: Layouts MUST work from phone width (about 360 px) to wide desktop with no horizontal page scrolling and touch targets of at least 44 px.
- **FR-018**: Animation MUST be omitted when the rider prefers reduced motion.
- **FR-019**: No stored data, route path, form field, calculation or notification behavior may change; every existing automated test MUST continue to pass, with test changes limited to assertions on old class names or copy that this restyle intentionally replaces.
- **FR-020**: Styling MUST remain plain CSS served from the application's static assets with no client-side framework and no build step to run or deploy, per constitution v1.3.0.

### Key Entities

This feature changes presentation only. It reads existing schedule status (overdue, due soon, on track, no estimate), days late or remaining, and the account's last successful sync time; it introduces no new stored data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rider can name the single most urgent maintenance task within 5 seconds of opening the page, in a week with five or more urgent tasks, without relying on color.
- **SC-002**: With 12 urgent tasks, the maintenance page shows no more than six tiles in the urgent area and fits without scrolling past them on a standard desktop screen.
- **SC-003**: Text and interactive-element contrast meets WCAG 2.1 AA in both themes on every page, verified automatically.
- **SC-004**: Every page remains fully usable at 360 px width with zero horizontal page scrolling.
- **SC-005**: Marking a task done updates the page with no full reload.
- **SC-006**: Every page, including fonts, loads fully styled with no external network requests and under 250 KB of styling and font assets.
- **SC-007**: The existing automated suite passes with no change in tested behavior, and no stored data, route or form field changes.

## Assumptions

- The theme follows the operating-system preference only; a manual toggle is out of scope.
- The accent is #FFA800 as chosen by the rider; the dark mockup default of teal is not used.
- "Urgent" means overdue, or due within the notification lead time already configured in settings; this reuses the existing status calculation.
- "View all" reveals the full urgent list on the same page using the existing page address with an extra display option, rather than a new page.
- The last-sync indicator reads the existing last successful Strava sync time; if none is recorded it shows "Not synced yet".
- Typeface files, if bundled, are committed as static assets; if they cannot be bundled, the system font fallback is acceptable.
- Existing partial-update behavior (Mark done, alert dismissal, delete confirmation) is reused; no new routes are needed.
- Supported browsers are the latest two major versions of Chrome, Safari, Firefox and Edge.
