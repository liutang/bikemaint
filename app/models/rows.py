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
