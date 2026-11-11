# Feature Specification: Bike Maintenance Tracker

**Feature Branch**: `001-bike-maintenance-tracker`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "I would like to build a bike maintenance tracker web app. It will keep track of my bikes, the components attached to them, and any components not currently installed. Components can be nested (tires install on rims). The app should regularly pull from my Strava ride data to update the mileage on each bike and component. I should be able to log maintenance against the bike and components. I should be able to schedule maintenance and check them off when done. The app should notify me when maintenance is due soon by calculating expected maintenance date based on riding behavior."

## Clarifications

### Session 2026-09-15

- Q: Should the app require its own login to be accessed, and if so, how? → A: Sign in with Strava — reuse the Strava OAuth connection itself as the app's login, with no separate password.
- Q: When a bike is first connected to a Strava gear entry, should the app import that gear's full past ride history, or only start counting mileage from the connection date forward? → A: The app's bike inventory is managed independently of Strava's gear list; the user manually pairs an app bike to a Strava gear entry, and once paired the app imports that gear's full ride history.
- Q: Where should the maintenance due-soon notification actually reach the user — in the app itself, via email, or both? → A: In-app and an outbound webhook (e.g., posting to a Discord channel via a user-configured webhook URL).
- Q: Can more than one component be installed under the same parent at the same time, or should each parent hold at most one installed child at a time? → A: Follow real-world bicycle assembly conventions — a parent may have multiple distinct child components where a real bike genuinely has multiple parts (e.g., a wheel has a hub, rim, and spokes), but the system must prevent physically implausible duplicates (e.g., two tires on the same rim, or two rims on the same hub).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintain a Garage Inventory (Priority: P1)

As the owner of one or more bikes, I want to record each of my bikes and every component on (or off) them, including how components nest inside one another (e.g., a tire mounted on a rim, mounted on a wheel, mounted on a bike), so that I have a single accurate picture of what's currently built up and what's sitting in storage.

**Why this priority**: This is the foundation everything else depends on. Without an accurate inventory of bikes and components and their nesting relationships, mileage tracking, maintenance logging, and scheduling have nothing to attach to. It is also independently useful on day one, even with mileage entered manually.

**Independent Test**: Can be fully tested by adding a bike, adding several components to it with nesting (e.g., wheel → rim → tire), removing a component to storage, and reinstalling it on a different bike — and confirming the inventory view reflects the current state accurately at every step.

**Acceptance Scenarios**:

1. **Given** an empty garage, **When** the user adds a new bike, **Then** the bike appears in the inventory with zero accumulated mileage.
2. **Given** an existing bike, **When** the user adds a component and marks it installed on that bike (optionally nested inside another installed component), **Then** the component appears attached to the bike in the correct nested position.
3. **Given** a component installed on a bike, **When** the user marks it as removed/uninstalled, **Then** it moves to an "in storage" list and stops being associated with that bike, while its maintenance and mileage history is preserved.
4. **Given** a component sitting in storage, **When** the user installs it on a different bike (or nested inside a different parent component), **Then** it appears under the new bike/parent and its historical mileage and maintenance log travel with it.

---

### User Story 2 - Automatic Mileage Tracking from Strava (Priority: P2)

As a rider who logs rides in Strava, I want the app to regularly pull my ride data and automatically add distance to the correct bike and its currently installed components, so that I don't have to manually track and re-enter mileage after every ride.

**Why this priority**: Automatic mileage tracking is the main time-saving payoff of the app and the input the maintenance-due predictions depend on, but the garage inventory (P1) must exist first for mileage to have somewhere to go.

**Independent Test**: Can be fully tested by connecting a Strava account, mapping a Strava bike/gear entry to an app bike, recording a ride in Strava, triggering a sync, and confirming the ride's distance is added to that bike and to every component currently installed on it (including nested ones).

**Acceptance Scenarios**:

1. **Given** the user has connected their Strava account and mapped a Strava gear entry to an app bike, **When** a new ride is recorded in Strava against that gear, **Then** the next sync adds the ride's distance to the bike's total mileage and to every component currently installed on that bike at the time of the ride.
2. **Given** a component was only installed for part of a bike's history, **When** mileage syncs for rides that occurred before it was installed, **Then** that mileage is not attributed to the component.
3. **Given** the Strava connection has not yet been made or has expired, **When** a sync runs, **Then** the app clearly flags that mileage may be stale and prompts the user to reconnect, without losing previously synced data.
4. **Given** the user disagrees with synced mileage (e.g., a ride was misattributed), **When** they make a manual mileage adjustment, **Then** the adjustment is recorded and reflected in the bike's/component's running total alongside an audit trail of the correction.

---

### User Story 3 - Log Completed Maintenance (Priority: P3)

As a bike owner, I want to record maintenance I've performed against a specific bike or component, including what was done and when, so that I have a complete service history I can refer back to.

**Why this priority**: Logging history is valuable on its own (answers "when did I last do this?") and is a prerequisite for calculating future due dates, but it depends on having bikes/components (P1) to log against.

**Independent Test**: Can be fully tested by selecting a bike or component, adding a maintenance entry with a description and date, and confirming it appears in that item's service history with the mileage at the time of service.

**Acceptance Scenarios**:

1. **Given** a bike or component exists, **When** the user logs a completed maintenance action against it, **Then** the entry is saved with a date, description, and the mileage at the time, and appears in that item's history.
2. **Given** a component's maintenance history exists, **When** the component is moved to a different bike, **Then** its maintenance history remains attached to the component, not the bike it was originally logged under.
3. **Given** a maintenance entry was logged in error, **When** the user edits or deletes it, **Then** the history and any dependent due-date calculations update accordingly.

---

### User Story 4 - Schedule Maintenance and Get Notified When It's Due (Priority: P4)

As a bike owner, I want to set up recurring or one-off maintenance tasks for a bike or component, have the app estimate when each one will next be due based on how much I actually ride, and be notified before it's due, so that I stay ahead of maintenance instead of discovering a problem mid-ride.

**Why this priority**: This is the "smart" capability that differentiates the app, but it builds directly on garage inventory (P1), mileage tracking (P2), and maintenance history (P3) — a completed maintenance log entry is what resets a schedule's due date.

**Independent Test**: Can be fully tested by creating a maintenance schedule on a component with a mileage and/or time interval, observing the app project a due date from recent riding pace, checking the task off once it's due, and confirming the next due date recalculates from that completion.

**Acceptance Scenarios**:

1. **Given** a bike or component has a maintenance schedule defined (e.g., "replace chain every 1,500 miles" or "grease headset every 12 months"), **When** the app has enough ride history to estimate riding pace, **Then** it projects a calendar due date by combining the remaining mileage (or time) against that pace.
2. **Given** a scheduled maintenance item's projected due date is within the notification lead time, **When** the check runs, **Then** the user receives a due-soon notification, and does not receive a duplicate notification for the same due cycle.
3. **Given** a scheduled maintenance item, **When** the user checks it off as done, **Then** it is logged as a completed maintenance entry (User Story 3) and the schedule's next due date/mileage recalculates from that completion point.
4. **Given** a component with an active schedule is moved to a different bike or into storage, **When** riding pace or installed status changes, **Then** the projected due date recalculates using the component's own accumulated mileage and current status rather than the old bike's pace.
5. **Given** insufficient ride history exists to estimate a reliable pace (e.g., a brand-new setup), **When** the app attempts to project a due date, **Then** it falls back to a time-based-only estimate or clearly indicates the projection is low-confidence rather than showing a misleading date.

---

### Edge Cases

- What happens when a Strava ride is recorded against gear that hasn't been mapped to any app bike yet?
- How does the system handle a component installed under multiple layers of nesting (e.g., tire → rim → wheel → bike) when the top-level bike is deleted — are nested components released to storage or deleted too?
- What happens when two maintenance schedules on the same component are simultaneously close to due (e.g., both a mileage-based and a time-based interval)?
- How does the system handle a gap in Strava data (e.g., rides logged manually in Strava without GPS, or a period where Strava access was revoked) when projecting riding pace?
- What happens when a user deletes a bike or component that has maintenance history or an active schedule attached?
- How does the system handle negative or corrected mileage (e.g., a Strava activity is deleted or edited after it was already synced)?
- What happens when a component is uninstalled and reinstalled multiple times across different bikes within the notification lead-time window?
- What happens when the user attempts to install a component into a position a real bike would only have one of, while another component already occupies that position (e.g., a second tire on a rim that already has one)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the user to create, view, edit, and delete bikes in their garage.
- **FR-002**: System MUST allow the user to create, view, edit, and delete components, and to mark each component as either installed (attached to a bike, optionally nested inside another installed component) or in storage (not currently installed on any bike).
- **FR-003**: System MUST support components nested to an arbitrary depth (e.g., tire installed on rim, rim installed on wheel, wheel installed on bike) and reflect this hierarchy in every view of a bike's build.
- **FR-004**: System MUST allow a component (and its full nested sub-tree, if any) to be moved between bikes, between parent components, or into/out of storage, while preserving its own accumulated mileage and maintenance history.
- **FR-005**: System MUST allow the user to connect their Strava account and authorize the app to read their ride activity data.
- **FR-006**: System MUST let the user manage their bike inventory independently of Strava's own gear list, and MUST allow the user to manually pair any app bike with a corresponding Strava gear entry; the app MUST NOT auto-create or auto-import bikes from Strava's gear list.
- **FR-007**: System MUST periodically sync new ride activity from Strava without requiring the user to manually trigger each sync.
- **FR-008**: System MUST add each synced ride's distance to the mapped bike's total mileage and to every component that was installed on that bike (at any nesting depth) at the time the ride occurred.
- **FR-009**: System MUST allow the user to manually adjust a bike's or component's mileage, and MUST retain a record that the adjustment was manual and why (if provided).
- **FR-010**: System MUST allow the user to log a completed maintenance entry against any bike or component, capturing at minimum a description, a date, and the mileage at the time of service.
- **FR-011**: System MUST display, for any bike or component, its full maintenance history in chronological order.
- **FR-012**: System MUST allow the user to edit or delete a previously logged maintenance entry.
- **FR-013**: System MUST allow the user to define a maintenance schedule on a bike or component, expressed as a mileage interval, a time interval, or both.
- **FR-014**: System MUST calculate a projected due date for each active maintenance schedule by converting the remaining mileage (or elapsed time) into a calendar estimate using the bike's/component's recent riding pace.
- **FR-015**: System MUST notify the user, both via an in-app alert and by posting to a user-configured outbound webhook (e.g., a Discord channel webhook), when a scheduled maintenance item's projected due date falls within a configurable lead-time window, and MUST NOT send duplicate notifications for the same due cycle.
- **FR-023**: System MUST allow the user to configure (add, edit, remove) the outbound webhook URL used for due-soon notifications.
- **FR-024**: System MUST validate component nesting against real-world bicycle assembly conventions: a parent may have multiple distinct child components installed at once where a real bike genuinely has multiple parts in that position (e.g., a wheel having a hub, rim, and spokes as separate installed components), but the system MUST reject installing a second component into a position that a real bike would only have one of (e.g., a second tire on a rim that already has one, or a second rim on a hub that already has one).
- **FR-016**: System MUST allow the user to mark a scheduled maintenance item as done, which MUST create a corresponding maintenance log entry (FR-010) and recalculate the schedule's next due point from the completion date/mileage.
- **FR-017**: System MUST recalculate a schedule's projected due date whenever the underlying component's installed status, parent bike, or riding pace changes.
- **FR-018**: System MUST indicate when a projected due date is a low-confidence estimate (e.g., insufficient ride history) rather than presenting it with the same certainty as a well-supported projection.
- **FR-019**: System MUST provide a single view summarizing all upcoming and overdue maintenance across every bike and component in the garage.
- **FR-020**: System MUST preserve a component's maintenance and mileage history when the component is removed from a bike, moved, or placed into storage, and MUST prompt the user for confirmation before permanently deleting any bike or component that has maintenance history or an active schedule.
- **FR-021**: System MUST require the user to sign in via their connected Strava account before granting access to any bike, component, maintenance, or schedule data; the app MUST NOT provide a separate username/password login.
- **FR-022**: When a bike is newly paired with a Strava gear entry, system MUST import that gear's full historical ride activity (not only rides going forward) and apply it to the bike's and its currently-installed components' accumulated mileage per FR-008.

### Key Entities

- **Bike**: A top-level ride-able asset owned by the user. Holds identifying details (name, type), total accumulated mileage, a mapping to a Strava gear entry, and the top-level components currently installed on it.
- **Component**: A physical part that can be installed on a bike or nested inside another component (e.g., a tire inside a rim), or sit unattached in storage. Holds its own accumulated mileage (independent of which bike it has ridden on), installation status, current parent (bike or component, if any), and its own maintenance history and schedules.
- **Maintenance Log Entry**: A record of a completed maintenance action against a specific bike or component, including description, date performed, and mileage at time of service.
- **Maintenance Schedule**: A recurring or one-off maintenance definition attached to a bike or component, expressed as a mileage interval, time interval, or both, used to project the next due date and drive notifications.
- **Ride Activity**: A synced record of a ride pulled from Strava, including distance, date, and the Strava gear it was recorded against, used both to accumulate mileage and to estimate riding pace for due-date projections.
- **Notification**: An alert generated when a maintenance schedule's projected due date enters the lead-time window, tied to a specific schedule and due cycle to prevent duplicates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A completed ride recorded in Strava is reflected in the correct bike's and components' mileage totals in the app within 24 hours, without any manual data entry.
- **SC-002**: A user can add a new bike with three nested components (e.g., bike → wheel → rim → tire) and see the correct nesting reflected in under 2 minutes.
- **SC-003**: 100% of mileage added to a bike during a sync is also correctly attributed to every component that was installed on that bike at the time of the corresponding ride.
- **SC-004**: For at least 95% of scheduled maintenance items with sufficient ride history, the user receives a due-soon notification before the item's projected due date is reached.
- **SC-005**: A user can view every overdue and upcoming maintenance item across their entire garage in a single screen, with no need to check each bike or component individually.
- **SC-006**: When a component is moved from one bike to another, its accumulated mileage and maintenance history are unchanged by the move, verifiable by comparing history before and after.

## Assumptions

- This is a single-user, personal application for one rider's own bikes and their own connected Strava account; multi-user/shared garages are out of scope for this feature.
- A component's accumulated mileage and maintenance history belong to the physical component itself and persist across moves between bikes or parent components, rather than being tied to a fixed "slot" on a bike.
- Maintenance schedules may be defined by mileage interval, time interval, or both; when both are set, whichever threshold is reached first determines the due date.
- Riding pace for due-date projection is estimated from the rider's recent ride history (e.g., a trailing window of recent activity) rather than all-time average, so projections stay responsive to changes in riding frequency.
- The default notification lead time is configurable but defaults to a reasonable early-warning window (e.g., roughly a week or a modest mileage buffer) rather than notifying only exactly on the due date.
- Notifications are delivered through an in-app alert/dashboard indicator and through a user-configured outbound webhook (e.g., posting to a Discord channel); additional channels (email, push) are a reasonable future enhancement but not required for this feature.
- A bike's mileage baseline is established automatically from Strava's full ride history once paired (FR-022); components (which Strava has no concept of) and any bike never paired to Strava still need a manually entered starting mileage and, optionally, backdated maintenance history, so due-date projections are meaningful from day one.
- Strava is the sole external data source for ride mileage in this feature; manual mileage adjustments are supported as a correction mechanism, not as a primary data entry method.
- If Strava access is not connected or lapses, previously synced mileage and history remain intact and usable; only new automatic syncing is affected.
