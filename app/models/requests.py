"""Pydantic request schemas validating input at the router boundary."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.component_kinds import (  # noqa: E402
    ALL_COMPONENT_TYPES,
    COMPONENT_TYPES,
    MULTI_INSTANCE_COMPONENT_TYPES,
)

def _validate_component_type(value: str) -> str:
    """New parts may only use the offered kinds."""
    if value not in COMPONENT_TYPES:
        raise ValueError(f"component_type must be one of {list(COMPONENT_TYPES)}")
    return value


def _validate_existing_component_type(value: str) -> str:
    """Editing may keep an older, finer kind; the service refuses switching *to* one."""
    if value not in ALL_COMPONENT_TYPES:
        raise ValueError(f"component_type must be one of {list(COMPONENT_TYPES)}")
    return value


class BikeCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    bike_type: str | None = None
    manual_baseline_mileage: float = Field(default=0.0, ge=0)


class BikeUpdateRequest(BikeCreateRequest):
    pass


BIKE_CATEGORIES: tuple[str, ...] = ("road", "gravel", "mountain", "hybrid", "e-bike", "other")


def _next_year() -> int:
    from datetime import date as _date

    return _date.today().year + 1


class BikeDetailsRequest(BaseModel):
    """Add/edit a bike by year, make, model and category (specs/005-unified-bike-screen).

    On edit, a bike with a single legacy name may leave year, make and model all blank; that
    rule lives in `bike_service`, so blank values are allowed through here as None.
    """

    year: int | None = None
    make: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=60)
    category: str
    manual_baseline_mileage: float = Field(default=0.0, ge=0)

    @field_validator("make", "model", mode="before")
    @classmethod
    def _trim(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("year", mode="before")
    @classmethod
    def _blank_year(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("year")
    @classmethod
    def _plausible_year(cls, value):
        if value is not None and not 1900 <= value <= _next_year():
            raise ValueError(f"Year must be between 1900 and {_next_year()}.")
        return value

    @field_validator("category")
    @classmethod
    def _known_category(cls, value):
        if value not in BIKE_CATEGORIES:
            raise ValueError("Choose a category from the list.")
        return value


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
        return _validate_existing_component_type(value)


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


_ROOT_PATTERN = r"^(bike|component):[0-9]{1,9}$"


class BuilderAddRequest(BaseModel):
    """Palette drop / Add control: create a new part of a type inside a screen's scope."""

    root: str = Field(pattern=_ROOT_PATTERN)
    component_type: str
    target: str = Field(pattern=r"^(storage|bike:[0-9]{1,9}|component:[0-9]{1,9})$")
    before_component_id: int | None = Field(default=None, ge=1)

    @field_validator("component_type")
    @classmethod
    def _check_component_type(cls, value: str) -> str:
        return _validate_component_type(value)

    def parents(self) -> dict[str, int | None]:
        return MoveTargetRequest(target=self.target).parents()


class BuilderMoveRequest(BaseModel):
    """Drag / Move-to / Garage / re-order: put a part on a parent (or storage), optionally before
    a sibling."""

    root: str = Field(pattern=_ROOT_PATTERN)
    component_id: int = Field(ge=1)
    target: str = Field(pattern=r"^(storage|bike:[0-9]{1,9}|component:[0-9]{1,9})$")
    before_component_id: int | None = Field(default=None, ge=1)

    def parents(self) -> dict[str, int | None]:
        return MoveTargetRequest(target=self.target).parents()


class BuilderDeleteRequest(BaseModel):
    """Trash: delete a part inside a screen's scope; `confirmed` answers the in-place question."""

    root: str = Field(pattern=_ROOT_PATTERN)
    component_id: int = Field(ge=1)
    confirmed: bool = False


class MaintenanceLogRequest(BaseModel):
    description: str = Field(min_length=1)
    performed_at: date
    performed_time: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    mileage_at_service: float | None = Field(default=None, ge=0)

    @field_validator("performed_time", mode="before")
    @classmethod
    def _blank_time(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


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


class RideRequest(BaseModel):
    """Add or edit a ride (specs/006-feedback-round-2): date, optional time, miles, note, bike."""

    ride_date: date
    ride_time: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    miles: float = Field(gt=0, le=5000)
    note: str | None = Field(default=None, max_length=200)
    bike_id: int | None = Field(default=None, ge=1)

    @field_validator("ride_time", "note", "bike_id", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value
