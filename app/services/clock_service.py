"""The rider's time zone (specs/023-settings-sync-and-timezone, 075).

Every stored time is a UTC instant (specs/075): times the rider types are read in the zone saved
in Settings (`to_utc`), and every time is shown in it (`format_utc`, `to_local`). "Today" is that
zone's date. Callable without FastAPI or request objects.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.db import accounts as accounts_db
from app.db import frames
from app.db.connection import get_connection


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


def to_utc(day: str, hhmm: str) -> str:
    """A date and minute the rider typed, read in the saved zone, as stored UTC text (specs/075 FR-001)."""
    return frames.to_utc(day, hhmm, _zone().key)


def to_local(value: str | None) -> str:
    """A stored instant as `YYYY-MM-DDTHH:MM` in the saved zone, to prefill a date and a time field."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return f"{moment.astimezone(_zone()):%Y-%m-%dT%H:%M}"


def keep_or_convert(stored: str | None, day: str, hhmm: str) -> str:
    """The stored instant when the form's date and minute are unchanged, else the new one (specs/075 FR-003)."""
    if stored and to_local(stored) == f"{day[:10]}T{hhmm[:5]}":
        return stored
    return to_utc(day, hhmm)


def keep_if_same(stored: str | None, new: str | None) -> str | None:
    """`stored` when `new` reads as the same local date and minute, else `new` (specs/075 FR-003)."""
    if stored and new and to_local(stored) == to_local(new):
        return stored
    return new


def end_of_day(day: str) -> str:
    """The last moment of a local date in the saved zone, as stored UTC text (a whole-day entry)."""
    return frames.end_of_day_utc(day, _zone().key)


def today() -> date:
    """Today's date in the saved zone (specs/075 FR-011)."""
    return _utc_now().astimezone(_zone()).date()


# The time zone picker: one representative zone per common UTC offset; daylight saving follows
# the real region, and the labels show the offset in force when the page is shown (specs/074).
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


def _utc_now() -> datetime:
    """The moment the picker labels describe (replaced in tests)."""
    return datetime.now(timezone.utc)


def offset_minutes(name: str, at: datetime) -> int:
    """The zone's UTC offset in minutes at `at`, daylight saving included (specs/074)."""
    return int(at.astimezone(ZoneInfo(name)).utcoffset() / timedelta(minutes=1))


def _gmt_offset(minutes: int) -> str:
    """"GMT-5", "GMT+5:30", "GMT+0": the standard offset as people write it."""
    sign = "-" if minutes < 0 else "+"
    hours, rest = divmod(abs(minutes), 60)
    return f"GMT{sign}{hours}" + (f":{rest:02d}" if rest else "")


def _label(name: str, at: datetime) -> str:
    """`(GMT-5) America/New York (EST)`: the offset at `at`, the zone's prominent city, its code.

    Offset and code follow daylight saving: the same entry reads `(GMT-4) ... (EDT)` in summer
    (specs/074, replacing the standard-time label of 023/027).

    The code is left out where there is no well-known one (the zone database then uses a number
    such as `-03`), and a note is added for the one common region that never changes its clocks.
    """
    local = at.astimezone(ZoneInfo(name))
    text = f"({_gmt_offset(offset_minutes(name, at))}) {name.replace('_', ' ')}"
    code = local.tzname() or ""
    if code and code[0] not in "+-" and code != name:
        note = ", no daylight saving" if name in _NO_DST_NOTE else ""
        text += f" ({code}{note})"
    return text


def timezone_choices(current: str, at: datetime | None = None) -> list[dict[str, str]]:
    """The picker's options as `{value, label}`, described at `at` (default: now), ordered by that offset.

    A saved zone that is not in the list is added first, marked "Current: ...", so it stays
    selectable and saving the form unchanged keeps it.
    """
    at = at or _utc_now()
    choices = [
        {"value": name, "label": _label(name, at)}
        for name in sorted(_PICKER_ZONES, key=lambda n: (offset_minutes(n, at), n != "Europe/London", n))
    ]
    if current not in _PICKER_ZONES:
        try:
            extra = f"Current: {_label(current, at)}"
        except Exception:
            extra = f"Current: {current}"
        choices.insert(0, {"value": current, "label": extra})
    return choices
