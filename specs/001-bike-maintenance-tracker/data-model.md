# Phase 1 Data Model: Bike Maintenance Tracker

All tables live in a single SQLite database. This is a single-user app (per spec Assumptions), so there is exactly one `account` row in practice, but the table still exists to hold the Strava OAuth tokens and webhook config cleanly rather than as loose global state.

## account

The signed-in rider and their Strava connection.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `strava_athlete_id` | INTEGER, UNIQUE, NOT NULL | Identifies the Strava account used to sign in (FR-021). |
| `strava_access_token` | TEXT, NOT NULL | Current access token. |
| `strava_refresh_token` | TEXT, NOT NULL | Used to mint new access tokens. |
| `strava_token_expires_at` | TEXT (ISO 8601), NOT NULL | |
| `strava_connected_at` | TEXT (ISO 8601), NOT NULL | |
| `strava_connection_stale` | BOOLEAN, NOT NULL, DEFAULT 0 | Set when token refresh fails or scope is revoked; drives the "mileage may be stale" UI (Acceptance Scenario US2-3). |
| `notification_webhook_url` | TEXT, NULLABLE | User-configured outbound webhook (FR-023). |
| `notification_lead_time_days` | INTEGER, NOT NULL, DEFAULT 7 | Default lead-time window (spec Assumptions). |
| `created_at` / `updated_at` | TEXT (ISO 8601) | |

## bike

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT, NOT NULL | |
| `bike_type` | TEXT, NULLABLE | e.g. road, gravel, MTB — free text. |
| `strava_gear_id` | TEXT, NULLABLE, UNIQUE | Set once paired (FR-006); NULL until then. |
| `strava_paired_at` | TEXT (ISO 8601), NULLABLE | Drives the one-time full-history backfill (FR-022). |
| `manual_baseline_mileage` | REAL, NOT NULL, DEFAULT 0 | Starting mileage entered by the user for bikes never paired to Strava, or before pairing (spec Assumptions). |
| `total_mileage` | REAL, NOT NULL, DEFAULT 0 | Denormalized running total = baseline + synced rides + manual adjustments; recomputed by the service layer, never edited directly by routers. |
| `is_deleted` | BOOLEAN, NOT NULL, DEFAULT 0 | Soft delete, see "Deletion" below. |
| `created_at` / `updated_at` | TEXT (ISO 8601) | |

## component

Self-referential tree; a component's parent is either a bike, another component, or nothing (storage).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT, NOT NULL | e.g. "Continental GP5000 rear tire". |
| `component_type` | TEXT, NOT NULL | Curated vocabulary (frame, wheel, hub, rim, tire, spoke, drivetrain, chain, brake, other); drives the multi-instance rule (research.md §3). |
| `parent_bike_id` | INTEGER, NULLABLE, FK → bike.id | Set when this is a top-level component directly on a bike. |
| `parent_component_id` | INTEGER, NULLABLE, FK → component.id | Set when nested inside another component. |
| `manual_baseline_mileage` | REAL, NOT NULL, DEFAULT 0 | Starting mileage for a component with prior life before entering the app. |
| `total_mileage` | REAL, NOT NULL, DEFAULT 0 | Own accumulated mileage; persists across moves (FR-004, SC-006). |
| `is_deleted` | BOOLEAN, NOT NULL, DEFAULT 0 | Soft delete. |
| `created_at` / `updated_at` | TEXT (ISO 8601) | |

**Invariant** (enforced in `app/services/`, not just the DB): at most one of `parent_bike_id` / `parent_component_id` is non-NULL at a time (both NULL = in storage). Installing a component under a parent that already holds a single-instance component of the same `component_type` is rejected (FR-024).

## component_installation_period

Tracks *when* a component was attached to a given parent, so historical ride mileage can be attributed correctly even after a component moves (Acceptance Scenario US2-2, FR-008).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `component_id` | INTEGER, NOT NULL, FK → component.id | |
| `parent_bike_id` | INTEGER, NULLABLE, FK → bike.id | The top-level bike this period's mileage rolls up to (denormalized from the chain of parents at the time, so a sync doesn't need to walk the tree for historical rides). |
| `parent_component_id` | INTEGER, NULLABLE, FK → component.id | Immediate parent during this period. |
| `installed_at` | TEXT (ISO 8601), NOT NULL | |
| `removed_at` | TEXT (ISO 8601), NULLABLE | NULL = currently installed. |

A new row is inserted every time a component is installed (onto a bike, another component, or moved); the prior open row (if any) gets `removed_at` set. Mileage sync (FR-008) attributes each `ride_activity` to a component only if the ride's date falls within one of its installation periods for that bike.

## ride_activity

A synced Strava activity.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `strava_activity_id` | INTEGER, UNIQUE, NOT NULL | Idempotency key for sync. |
| `strava_gear_id` | TEXT, NULLABLE | As reported by Strava; NULL/unmapped rides are recorded but not attributed (Edge Case: unmapped gear). |
| `bike_id` | INTEGER, NULLABLE, FK → bike.id | Resolved from `strava_gear_id` at sync time; NULL if unmapped. |
| `distance_miles` | REAL, NOT NULL | |
| `occurred_at` | TEXT (ISO 8601), NOT NULL | Ride start date/time, used for both mileage attribution and pace-window calculations. |
| `is_deleted_upstream` | BOOLEAN, NOT NULL, DEFAULT 0 | Set if Strava reports the activity deleted after sync; totals are recomputed excluding it (Edge Case: corrected mileage). |
| `synced_at` | TEXT (ISO 8601), NOT NULL | |

## mileage_adjustment

An audit trail of manual corrections (FR-009).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `bike_id` | INTEGER, NULLABLE, FK → bike.id | Exactly one of `bike_id` / `component_id` is set. |
| `component_id` | INTEGER, NULLABLE, FK → component.id | |
| `delta_miles` | REAL, NOT NULL | Signed; can be negative (e.g. correcting an over-attributed ride). |
| `reason` | TEXT, NULLABLE | User-supplied explanation. |
| `created_at` | TEXT (ISO 8601), NOT NULL | |

## maintenance_log_entry

Completed maintenance (FR-010, User Story 3).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `bike_id` | INTEGER, NULLABLE, FK → bike.id | Exactly one of `bike_id` / `component_id` is set. |
| `component_id` | INTEGER, NULLABLE, FK → component.id | Stays with the component across moves (Acceptance Scenario US3-2). |
| `description` | TEXT, NOT NULL | |
| `performed_at` | TEXT (ISO 8601), NOT NULL | |
| `mileage_at_service` | REAL, NOT NULL | Snapshot of the item's `total_mileage` at the time. |
| `schedule_id` | INTEGER, NULLABLE, FK → maintenance_schedule.id | Set when this entry was created by checking off a schedule (FR-016); NULL for free-standing log entries. |
| `created_at` / `updated_at` | TEXT (ISO 8601) | |

## maintenance_schedule

A recurring or one-off maintenance definition (FR-013, User Story 4).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `bike_id` | INTEGER, NULLABLE, FK → bike.id | Exactly one of `bike_id` / `component_id` is set. |
| `component_id` | INTEGER, NULLABLE, FK → component.id | |
| `name` | TEXT, NOT NULL | e.g. "Replace chain". |
| `interval_miles` | REAL, NULLABLE | At least one of `interval_miles` / `interval_days` is set. |
| `interval_days` | INTEGER, NULLABLE | |
| `baseline_mileage` | REAL, NOT NULL | The item's `total_mileage` as of the last completion (or creation, if never completed). |
| `baseline_date` | TEXT (ISO 8601), NOT NULL | Last completion date (or creation date). |
| `cycle_number` | INTEGER, NOT NULL, DEFAULT 1 | Incremented every completion; used as the notification dedup key (research.md §5). |
| `is_active` | BOOLEAN, NOT NULL, DEFAULT 1 | Deactivated schedules stop projecting/notifying but keep history. |
| `created_at` / `updated_at` | TEXT (ISO 8601) | |

Projected due date/mileage is *computed*, not stored (research.md §4), so it always reflects current pace, install status, and parent — recalculating on every read satisfies FR-017 without a background job having to chase every dependency change.

## notification

Recorded due-soon alerts (FR-015), keyed for de-duplication.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `schedule_id` | INTEGER, NOT NULL, FK → maintenance_schedule.id | |
| `cycle_number` | INTEGER, NOT NULL | Snapshot of the schedule's cycle at send time. UNIQUE together with `schedule_id`. |
| `projected_due_at` | TEXT (ISO 8601), NOT NULL | The due date that triggered this notification. |
| `webhook_delivered` | BOOLEAN, NOT NULL, DEFAULT 0 | |
| `webhook_delivery_error` | TEXT, NULLABLE | Last delivery error, if any (Principle V: human-readable). |
| `acknowledged_at` | TEXT (ISO 8601), NULLABLE | When the user dismissed the in-app alert. |
| `created_at` | TEXT (ISO 8601), NOT NULL | |

`UNIQUE(schedule_id, cycle_number)` is the enforcement mechanism for "no duplicate notification for the same due cycle" (FR-015).

## Deletion semantics (FR-020, Edge Cases)

- Bikes and components are **soft-deleted** (`is_deleted`), never hard-deleted, so maintenance/mileage history and audit trails are never lost.
- Deleting a bike with installed components: the service layer requires the user to first move each top-level component to storage or another bike (mirrors real-world disassembly); the route surfaces this as a confirmation step rather than silently cascading, per FR-020's "prompt the user for confirmation before permanently deleting any bike or component that has maintenance history or an active schedule."
- Deleting a component recursively soft-deletes its installed sub-tree along with it, since a sub-component cannot meaningfully exist installed under a deleted parent; each affected component's history remains queryable directly by id even though it no longer appears in the live inventory view.

## Entity relationship summary

```
account (1) ── (0..1 active session)
bike (1) ── (0..*) component [top-level, via parent_bike_id]
component (1) ── (0..*) component [nested, via parent_component_id]
bike / component (1) ── (0..*) component_installation_period
bike (1) ── (0..*) ride_activity [via resolved gear mapping]
bike / component (1) ── (0..*) mileage_adjustment
bike / component (1) ── (0..*) maintenance_log_entry
bike / component (1) ── (0..*) maintenance_schedule
maintenance_schedule (1) ── (0..*) maintenance_log_entry [via schedule_id]
maintenance_schedule (1) ── (0..*) notification
```
