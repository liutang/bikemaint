"""The rider's time zone, for display (specs/023-settings-sync-and-timezone).

Times the app records in UTC (Strava rides, completed-task times, connected-since) are shown in
the zone saved in Settings. Display only: no stored time is converted, and typed times are shown
as typed. Callable without FastAPI or request objects.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.db import accounts as accounts_db
from app.db.connection import get_connection

_STORED_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Zone name per database file, so a lookup is not a query every time a time is rendered.
_cache: dict[str, str] = {}


def _key() -> str:
    return os.environ.get("DATABASE_PATH", "")


def zone_name() -> str:
    """The saved zone name (`UTC` until the rider chooses one)."""
    key = _key()
    if key not in _cache:
        try:
            with get_connection() as conn:
                account = accounts_db.get_singleton(conn)
        except Exception:
            return "UTC"
        _cache[key] = account.timezone if account is not None else "UTC"
    return _cache[key]


def remember_zone(name: str) -> None:
    """Called when the rider saves a zone, so the next page already uses it."""
    _cache[_key()] = name


_clock_cache: dict[str, str] = {}


def clock_format() -> str:
    """`12` (default) or `24`: how displayed times are written (specs/036)."""
    key = _key()
    if key not in _clock_cache:
        try:
            with get_connection() as conn:
                account = accounts_db.get_singleton(conn)
        except Exception:
            return "12"
        _clock_cache[key] = account.clock_format if account is not None else "12"
    return _clock_cache[key]


def remember_clock(value: str) -> None:
    _clock_cache[_key()] = value


def _clock(moment: datetime) -> str:
    """`h:MMAM` on the 12-hour clock (2:26PM), `HH:MM` on the 24-hour one."""
    if clock_format() == "24":
        return f"{moment:%H:%M}"
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment:%M}{'AM' if moment.hour < 12 else 'PM'}"


def _wall_moment(value: str | None) -> datetime | None:
    """A stored moment as a wall-clock time in the chosen zone, or None if it is not a time.

    Typed times are stored as typed, always whole minutes, and are shown as typed. A moment the app
    recorded itself (such as installing a part "now") carries seconds or microseconds and is a UTC
    instant, so it is converted to the chosen zone (specs/023 FR-008, amended by 049).
    """
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.second or moment.microsecond:
        return moment.astimezone(_zone()).replace(tzinfo=None)  # `Z` text is read as UTC
    return moment.replace(tzinfo=None)


def format_wall(value: str | None) -> str:
    """A stored time as `YYYY-MM-DD time`, no zone label; other text is returned as is."""
    if not value:
        return ""
    moment = _wall_moment(value)
    return value if moment is None else f"{moment:%Y-%m-%d} {_clock(moment)}"


def to_wall(value: str | None) -> str:
    """Like `format_wall` but as `YYYY-MM-DDTHH:MM`, to prefill a date and a time field."""
    if not value:
        return ""
    moment = _wall_moment(value)
    return value if moment is None else f"{moment:%Y-%m-%dT%H:%M}"


def _zone() -> ZoneInfo:
    try:
        return ZoneInfo(zone_name())
    except Exception:
        return ZoneInfo("UTC")


def format_utc(value: str | None) -> str:
    """A stored UTC time as `YYYY-MM-DD time ABBR` in the saved zone and clock; other text is returned as is."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(_zone())
    return f"{local:%Y-%m-%d} {_clock(local)} {local:%Z}"


def now_in_zone_moment() -> str:
    """The current wall-clock time in the saved zone, in the stored text format.

    For comparing with times the rider typed, which are wall-clock times (never for values that
    are stored, which stay in UTC).
    """
    return datetime.now(_zone()).replace(tzinfo=None).strftime(_STORED_FORMAT)


# The time zone picker: one representative standard zone per common UTC offset, so the rider
# chooses "-05:00 EST" and daylight saving still follows the real region (EST becomes EDT).
# Not a list of countries and cities. Order does not matter here; choices are sorted by offset.
_PICKER_ZONES: tuple[str, ...] = (
    "Pacific/Pago_Pago", "Pacific/Honolulu", "America/Anchorage", "America/Los_Angeles",
    "America/Denver", "America/Phoenix", "America/Chicago", "America/New_York",
    "America/Halifax", "America/St_Johns", "America/Sao_Paulo", "Atlantic/South_Georgia",
    "Atlantic/Azores", "Europe/London", "UTC", "Europe/Paris", "Europe/Athens",
    "Europe/Moscow", "Asia/Tehran", "Asia/Dubai", "Asia/Kabul", "Asia/Karachi",
    "Asia/Kolkata", "Asia/Kathmandu", "Asia/Dhaka", "Asia/Yangon", "Asia/Bangkok",
    "Asia/Shanghai", "Asia/Tokyo", "Australia/Adelaide", "Australia/Sydney",
    "Pacific/Noumea", "Pacific/Auckland",
)
# Where a common region shares an offset and abbreviation with another but never changes clocks.
_NO_DST_NOTE = {"America/Phoenix"}


def _standard_time(name: str) -> datetime:
    """A moment in the zone's standard (non-summer) time: the smaller of its January and July offsets."""
    zone = ZoneInfo(name)
    january = datetime(2026, 1, 15, 12, tzinfo=zone)
    july = datetime(2026, 7, 15, 12, tzinfo=zone)
    return january if january.utcoffset() <= july.utcoffset() else july


def standard_offset_minutes(name: str) -> int:
    return int(_standard_time(name).utcoffset() / timedelta(minutes=1))


def _gmt_offset(minutes: int) -> str:
    """"GMT-5", "GMT+5:30", "GMT+0": the standard offset as people write it."""
    sign = "-" if minutes < 0 else "+"
    hours, rest = divmod(abs(minutes), 60)
    return f"GMT{sign}{hours}" + (f":{rest:02d}" if rest else "")


def _label(name: str) -> str:
    """`(GMT-5) America/New York (EST)`: standard offset, the zone's prominent city, its code.

    The code is left out where there is no well-known one (the zone database then uses a number
    such as `-03`), and a note is added for the one common region that never changes its clocks.
    """
    offset = standard_offset_minutes(name)
    text = f"({_gmt_offset(offset)}) {name.replace('_', ' ')}"
    code = _standard_time(name).tzname() or ""
    if code and code[0] not in "+-" and code != name:
        note = ", no daylight saving" if name in _NO_DST_NOTE else ""
        text += f" ({code}{note})"
    return text


def timezone_choices(current: str) -> list[dict[str, str]]:
    """The picker's options as `{value, label}`, ordered by offset.

    A saved zone that is not in the list is added first, marked "Current: ...", so it stays
    selectable and saving the form unchanged keeps it.
    """
    choices = [
        {"value": name, "label": _label(name)}
        for name in sorted(_PICKER_ZONES, key=lambda n: (standard_offset_minutes(n), n != "Europe/London", n))
    ]
    if current not in _PICKER_ZONES:
        try:
            extra = f"Current: {_label(current)}"
        except Exception:
            extra = f"Current: {current}"
        choices.insert(0, {"value": current, "label": extra})
    return choices
