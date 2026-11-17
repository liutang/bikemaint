"""Zone arithmetic for stored times (specs/075 research §1-§2)."""

from datetime import datetime, timezone

from app.db import frames

NY = "America/New_York"


def test_stored_format_is_utc_with_microseconds():
    assert frames.STORED_FORMAT == "%Y-%m-%dT%H:%M:%S.%fZ"


def test_to_utc_reads_the_time_in_the_zone_of_that_date():
    assert frames.to_utc("2026-11-16", "17:39", NY) == "2026-11-16T22:39:00.000000Z"  # EST
    assert frames.to_utc("2026-07-04", "09:00", NY) == "2026-07-04T13:00:00.000000Z"  # EDT


def test_to_utc_reads_a_nonexistent_time_with_the_offset_before_the_change():
    # 2:30 AM does not exist on 2026-03-08; it is read as EST, which is 3:30 AM EDT.
    assert frames.to_utc("2026-03-08", "02:30", NY) == "2026-03-08T07:30:00.000000Z"


def test_to_utc_reads_a_repeated_time_as_the_first_one():
    assert frames.to_utc("2026-11-01", "01:30", NY) == "2026-11-01T05:30:00.000000Z"  # EDT


def test_to_utc_in_utc_is_the_identity():
    assert frames.to_utc("2026-11-16", "17:39", "UTC") == "2026-11-16T17:39:00.000000Z"


def test_from_utc_gives_the_local_moment():
    local = frames.from_utc("2026-11-16T22:39:00.000000Z", NY)
    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 11, 16, 17, 39)
    assert local.tzname() == "EST"
    assert frames.from_utc("2026-11-16T22:39:00Z", NY) == local
    assert frames.from_utc("2026-11-16T22:39:00Z", NY).astimezone(timezone.utc) == datetime(
        2026, 11, 16, 22, 39, tzinfo=timezone.utc
    )


def test_end_of_day_utc_is_the_last_moment_of_the_local_day():
    assert frames.end_of_day_utc("2026-11-16", NY) == "2026-11-17T04:59:59.999999Z"
    assert frames.end_of_day_utc("2026-07-04", NY) == "2026-07-05T03:59:59.999999Z"
