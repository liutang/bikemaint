"""Pydantic request schemas validating input at the router boundary."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

# Curated vocabulary (research.md §3): drives the FR-024 single-instance-per-type-per-parent
# rule below. Types not in MULTI_INSTANCE_COMPONENT_TYPES may appear at most once under
# any given parent (bike, component, or storage).
COMPONENT_TYPES: tuple[str, ...] = (
    "frame",
    "wheel",
    "hub",
    "rim",
    "tire",
    "spoke",
    "bolt",
    "pad",
    "drivetrain",
    "chain",
    "brake",
    "other",
)

MULTI_INSTANCE_COMPONENT_TYPES: frozenset[str] = frozenset({"spoke", "bolt", "pad", "other"})


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


class MaintenanceLogRequest(BaseModel):
    description: str = Field(min_length=1)
    performed_at: date
    mileage_at_service: float | None = Field(default=None, ge=0)
