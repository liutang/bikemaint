"""The year of a typed date (specs/076 research §1).

A browser date field sends what was typed for the year, zero-padded: typing 7/17/26 sends
`0026-07-17`. The rider chose that a year from 0 to 99 means 2000 to 2099 ("20xx is fine"). Years
from 100 to 1899 are typos and are refused. Text that is not `YYYY-MM-DD` is left for the field's
own validation to report.
"""

from __future__ import annotations

import re

from pydantic_core import PydanticCustomError

_TYPED = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
FIRST_YEAR = 1900


def full_year(value):
    """`YYYY-MM-DD` with a year below 100 read as 20yy; years 100 to 1899 refused."""
    if not isinstance(value, str):
        return value
    match = _TYPED.match(value)
    if match is None:
        return value
    year = int(match.group(1))
    if year < 100:
        year += 2000
    elif year < FIRST_YEAR:
        raise PydanticCustomError("date", "Enter a valid date")
    return f"{year:04d}-{match.group(2)}-{match.group(3)}"
