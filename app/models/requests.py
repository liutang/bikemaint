"""Pydantic request schemas validating input at the router boundary."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.component_kinds import (  # noqa: E402
    COMPONENT_TYPES,
    MULTI_INSTANCE_COMPONENT_TYPES,
)

def _validate_component_type(value: str) -> str:
    if value not in COMPONENT_TYPES:
        raise ValueError(f"component_type must be one of {sorted(COMPONENT_TYPES)}")
    return value


class BikeCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    bike_type: str | None = None
    manual_baseline_mileage: float = Field(default=0.0, ge=0)


class BikeUpdateRequest(BikeCreateRequest):
    pass


class BikeCatalogRequest(BaseModel):
    """Add/edit a bike by catalog entry. Only the id's shape is checked here; membership in the
    catalog (and whether `__keep__` is allowed) is decided by `app/services/bike_service.py`."""

    catalog_id: str = Field(pattern=r"^(__keep__|[a-z0-9]+(-[a-z0-9]+)*)$", max_length=64)
    manual_baseline_mileage: float = Field(default=0.0, ge=0)


class _ComponentParentFields(BaseModel):
    parent_bike_id: int | None = None
    parent_component_id: int | None = None

    @model_validator(mode="after")
    def _validate_single_parent(self) -> "_ComponentParentFields":
        if self.parent_bike_id is not None and self.parent_component_id is not None:
            raise ValueError(
                "A component may have at most one parent: a bike, another component, or "
                "neither (storage)."
            )
        return self


class ComponentCreateRequest(_ComponentParentFields):
    name: str = Field(min_length=1)
    component_type: str
    manual_baseline_mileage: float = Field(default=0.0, ge=0)

    @field_validator("component_type")
    @classmethod
    def _check_component_type(cls, value: str) -> str:
        return _validate_component_type(value)


class ComponentUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    component_type: str
    manual_baseline_mileage: float = Field(default=0.0, ge=0)

    @field_validator("component_type")
    @classmethod
    def _check_component_type(cls, value: str) -> str:
        return _validate_component_type(value)


class ComponentMoveRequest(_ComponentParentFields):
    pass


class MoveTargetRequest(BaseModel):
    """The "Move to..." choice: `storage`, `bike:ID` or `component:ID` (ids checked by the service)."""

    target: str = Field(pattern=r"^(storage|bike:[0-9]{1,9}|component:[0-9]{1,9})$")

    def parents(self) -> dict[str, int | None]:
        kind, _, raw = self.target.partition(":")
        value = int(raw) if raw else None
        return {
            "parent_bike_id": value if kind == "bike" else None,
            "parent_component_id": value if kind == "component" else None,
        }


class MaintenanceLogRequest(BaseModel):
    description: str = Field(min_length=1)
    performed_at: date
    mileage_at_service: float | None = Field(default=None, ge=0)


class ScheduleRequest(BaseModel):
    name: str = Field(min_length=1)
    interval_miles: float | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def _require_an_interval(self) -> "ScheduleRequest":
        if self.interval_miles is None and self.interval_days is None:
            raise ValueError("Set a mileage interval, a time interval, or both.")
        return self


class WebhookSettingsRequest(BaseModel):
    notification_webhook_url: str | None = None

    @field_validator("notification_webhook_url")
    @classmethod
    def _http_or_https_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return value


class LeadTimeSettingsRequest(BaseModel):
    notification_lead_time_days: int = Field(ge=0, le=365)


class ThemeSettingsRequest(BaseModel):
    theme: Literal["system", "light", "dark"]
