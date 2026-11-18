"""Helpers that turn validation failures into template context for inline form errors.

Routers pass the result to the template so each error can be shown beside its field,
while the full list of messages still feeds the form-level summary.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from app.models.typed_dates import full_year

# Typed date fields, shown back with the year read the way it is saved (specs/076 FR-005).
_DATE_FIELDS = ("ride_date", "performed_at", "installed_date", "removed_date")


def _values(form: Mapping[str, str]) -> dict:
    values = dict(form)
    for name in _DATE_FIELDS:
        if name in values:
            try:
                values[name] = full_year(values[name])
            except PydanticCustomError:
                pass  # a refused year is shown as typed
    return values


def field_errors(exc: ValidationError) -> dict[str, str]:
    """Map each failing field to its first error message.

    Errors without a field (model-level validators) are left out; they only appear in
    the summary list.
    """
    result: dict[str, str] = {}
    for error in exc.errors():
        location = error["loc"]
        if not location:
            continue
        result.setdefault(str(location[0]), error["msg"])
    return result


def error_context(form: Mapping[str, str], exc: ValidationError) -> dict:
    """Template context for a re-rendered form: summary, per-field errors, entered values."""
    return {
        "errors": [error["msg"] for error in exc.errors()],
        "field_errors": field_errors(exc),
        "values": _values(form),
    }


def message_context(form: Mapping[str, str], message: str, field: str | None = None) -> dict:
    """Like `error_context` for a failure that did not come from Pydantic validation."""
    return {
        "errors": [message],
        "field_errors": {field: message} if field else {},
        "values": _values(form),
    }
