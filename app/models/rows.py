"""Typed row dataclasses for the tables created in app/db/migrations/0001_initial.sql.

Each dataclass mirrors a table's columns exactly and provides `from_row` to build
an instance from the `sqlite3.Row` objects returned by `app/db/` query functions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: int
    strava_athlete_id: int
    strava_access_token: str
    strava_refresh_token: str
    strava_token_expires_at: str
    strava_connected_at: str
    strava_connection_stale: bool
    notification_webhook_url: str | None
    notification_lead_time_days: int
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Account:
        return cls(
            id=row["id"],
            strava_athlete_id=row["strava_athlete_id"],
            strava_access_token=row["strava_access_token"],
            strava_refresh_token=row["strava_refresh_token"],
            strava_token_expires_at=row["strava_token_expires_at"],
            strava_connected_at=row["strava_connected_at"],
            strava_connection_stale=bool(row["strava_connection_stale"]),
            notification_webhook_url=row["notification_webhook_url"],
            notification_lead_time_days=row["notification_lead_time_days"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True)
class Bike:
    id: int
    name: str
    bike_type: str | None
    strava_gear_id: str | None
    strava_paired_at: str | None
    manual_baseline_mileage: float
    total_mileage: float
    is_deleted: bool
    created_at: str
    updated_at: str
    year: int | None = None
    make: str | None = None
    model: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Bike:
        return cls(
            id=row["id"],
            name=row["name"],
            bike_type=row["bike_type"],
            strava_gear_id=row["strava_gear_id"],
            strava_paired_at=row["strava_paired_at"],
            manual_baseline_mileage=row["manual_baseline_mileage"],
            total_mileage=row["total_mileage"],
            is_deleted=bool(row["is_deleted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            year=row["year"],
            make=row["make"],
            model=row["model"],
        )


@dataclass(frozen=True)
class Component:
    id: int
    name: str
    component_type: str
    parent_bike_id: int | None
    parent_component_id: int | None
    manual_baseline_mileage: float
    total_mileage: float
    is_deleted: bool
    created_at: str
    updated_at: str
    position: int = 0

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Component:
        return cls(
            id=row["id"],
            name=row["name"],
            component_type=row["component_type"],
            parent_bike_id=row["parent_bike_id"],
            parent_component_id=row["parent_component_id"],
            manual_baseline_mileage=row["manual_baseline_mileage"],
            total_mileage=row["total_mileage"],
            is_deleted=bool(row["is_deleted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            position=row["position"],
        )


@dataclass(frozen=True)
class ComponentInstallationPeriod:
    id: int
    component_id: int
    parent_bike_id: int | None
    parent_component_id: int | None
    installed_at: str
    removed_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ComponentInstallationPeriod:
        return cls(
            id=row["id"],
            component_id=row["component_id"],
            parent_bike_id=row["parent_bike_id"],
            parent_component_id=row["parent_component_id"],
            installed_at=row["installed_at"],
            removed_at=row["removed_at"],
        )


@dataclass(frozen=True)
class RideActivity:
    id: int
    source: str  # "strava" or "manual"
    strava_activity_id: int | None
    strava_gear_id: str | None
    bike_id: int | None
    distance_miles: float
    occurred_at: str
    note: str | None
    is_deleted_upstream: bool
    deleted_by_user: bool
    user_modified: bool
    synced_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RideActivity:
        return cls(
            id=row["id"],
            source=row["source"],
            strava_activity_id=row["strava_activity_id"],
            strava_gear_id=row["strava_gear_id"],
            bike_id=row["bike_id"],
            distance_miles=row["distance_miles"],
            occurred_at=row["occurred_at"],
            note=row["note"],
            is_deleted_upstream=bool(row["is_deleted_upstream"]),
            deleted_by_user=bool(row["deleted_by_user"]),
            user_modified=bool(row["user_modified"]),
            synced_at=row["synced_at"],
        )


@dataclass(frozen=True)
class MileageAdjustment:
    id: int
    bike_id: int | None
    component_id: int | None
    delta_miles: float
    reason: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> MileageAdjustment:
        return cls(
            id=row["id"],
            bike_id=row["bike_id"],
            component_id=row["component_id"],
            delta_miles=row["delta_miles"],
            reason=row["reason"],
            created_at=row["created_at"],
        )


@dataclass(frozen=True)
class MaintenanceLogEntry:
    id: int
    bike_id: int | None
    component_id: int | None
    description: str
    performed_at: str
    mileage_at_service: float
    schedule_id: int | None
    created_at: str
    updated_at: str
    kind: str = "service"  # "service" (logged work) or "event" (parts added/removed)
    performed_time: str | None = None  # optional HH:MM typed by the rider

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> MaintenanceLogEntry:
        return cls(
            id=row["id"],
            bike_id=row["bike_id"],
            component_id=row["component_id"],
            description=row["description"],
            performed_at=row["performed_at"],
            mileage_at_service=row["mileage_at_service"],
            schedule_id=row["schedule_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            kind=row["kind"],
            performed_time=row["performed_time"],
        )


@dataclass(frozen=True)
class MaintenanceSchedule:
    id: int
    bike_id: int | None
    component_id: int | None
    name: str
    interval_miles: float | None
    interval_days: int | None
    baseline_mileage: float
    baseline_date: str
    cycle_number: int
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> MaintenanceSchedule:
        return cls(
            id=row["id"],
            bike_id=row["bike_id"],
            component_id=row["component_id"],
            name=row["name"],
            interval_miles=row["interval_miles"],
            interval_days=row["interval_days"],
            baseline_mileage=row["baseline_mileage"],
            baseline_date=row["baseline_date"],
            cycle_number=row["cycle_number"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True)
class Notification:
    id: int
    schedule_id: int
    cycle_number: int
    projected_due_at: str
    webhook_delivered: bool
    webhook_delivery_error: str | None
    acknowledged_at: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Notification:
        return cls(
            id=row["id"],
            schedule_id=row["schedule_id"],
            cycle_number=row["cycle_number"],
            projected_due_at=row["projected_due_at"],
            webhook_delivered=bool(row["webhook_delivered"]),
            webhook_delivery_error=row["webhook_delivery_error"],
            acknowledged_at=row["acknowledged_at"],
            created_at=row["created_at"],
        )
