"""Display formats for numbers, such as mileage with thousands separators (specs/059-comma-mileage).

Display only: form inputs and stored values never use these. Callable without FastAPI.
"""

from __future__ import annotations


def num1(value: float | None) -> str:
    """One decimal with thousands separators: `12,345.6`."""
    return "" if value is None else f"{value:,.1f}"


def num0(value: float | None) -> str:
    """Whole number with thousands separators: `1,991`."""
    return "" if value is None else f"{value:,.0f}"


def count(value: float) -> str:
    """A count without a trailing `.0` but with separators: `1,000`, `2.5`, `1,234.5`."""
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}".rstrip("0").rstrip(".")
