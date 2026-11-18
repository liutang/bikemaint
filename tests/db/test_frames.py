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


# ------------------------------------------------ specs/076 FR-004: four-digit years on every platform


def test_stored_writes_a_four_digit_year():
    assert frames.stored(datetime(999, 1, 2, 3, 4, 5, tzinfo=timezone.utc)) == "0999-01-02T03:04:05.000000Z"
    assert frames.stored(datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)) == "2026-11-18T09:00:00.000000Z"


def test_to_utc_and_end_of_day_keep_four_digit_years():
    # glibc's strftime("%Y") writes "21" here; macOS writes "0021" (specs/076 Background).
    assert frames.to_utc("0021-04-18", "00:00", "UTC").startswith("0021-04-18T")
    assert frames.end_of_day_utc("0021-04-18", "UTC") == "0021-04-18T23:59:59.999999Z"


def test_the_writers_use_stored_rather_than_strftime_year(monkeypatch):
    calls = []
    real = frames.stored
    monkeypatch.setattr(frames, "stored", lambda dt: calls.append(dt) or real(dt))
    frames.to_utc("2026-11-16", "17:39", NY)
    frames.end_of_day_utc("2026-11-16", NY)
    assert len(calls) == 2
