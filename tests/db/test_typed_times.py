"""The one-time conversion of typed times to UTC (specs/075 US3)."""

import sqlite3

import pytest

from app.db import accounts, bikes, components, connection, mileage, typed_times
from app.db import maintenance as maintenance_db

NY = "America/New_York"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "bikemaint.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _account(conn, zone=NY):
    account = accounts.upsert_from_strava(
        conn, strava_athlete_id=1, access_token="a", refresh_token="r", expires_at="2099-01-01T00:00:00Z"
    )
    accounts.update_timezone(conn, account.id, zone)


def _value(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def _manual(conn, bike, when, miles=1.0, deleted=False):
    ride = mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=miles, occurred_at=when, note=None)
    if deleted:
        conn.execute("UPDATE ride_activity SET deleted_by_user = 1 WHERE id = ?", (ride.id,))
    return ride.id


def _strava(conn, bike, n, when, miles=1.0, edited=False):
    mileage.upsert_ride_activity(
        conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles, occurred_at=when
    )
    ride_id = _value(conn, "SELECT id FROM ride_activity WHERE strava_activity_id = ?", n)
    if edited:
        conn.execute("UPDATE ride_activity SET user_modified = 1 WHERE id = ?", (ride_id,))
    return ride_id


def _entry(conn, *, bike=None, part=None, day, time=None):
    return maintenance_db.create(
        conn, bike_id=bike.id if bike else None, component_id=part.id if part else None, description="Lube/Wax",
        performed_at=day, performed_time=time, mileage_at_service=7.5,
    ).id


def _schedule(conn, bike, baseline_at):
    cursor = conn.execute(
        "INSERT INTO maintenance_schedule (bike_id, name, interval_miles, baseline_mileage, baseline_date, "
        "cycle_number, is_active, created_at, updated_at, baseline_at) "
        "VALUES (?, 'Lube', 100, 0, '2026-11-16', 1, 1, '2026-11-16T12:00:00.000000Z', '2026-11-16T12:00:00.000000Z', ?)",
        (bike.id, baseline_at),
    )
    return cursor.lastrowid


# ------------------------------------------------ convert(conn, zone): one case per row of the US3 table


def test_manual_rides_are_converted_deleted_ones_too(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        live = _manual(conn, bike, "2026-11-16T17:00:00.000000Z")
        gone = _manual(conn, bike, "2026-07-04T09:00:00.000000Z", deleted=True)
        typed_times.convert(conn, NY)
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", live) == "2026-11-16T22:00:00.000000Z"
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", gone) == "2026-07-04T13:00:00.000000Z"


def test_strava_rides_edited_or_not_are_left_alone(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        plain = _strava(conn, bike, 1, "2026-11-13T19:26:00.000000Z")
        edited = _strava(conn, bike, 2, "2026-11-14T19:00:00.000000Z", edited=True)
        typed_times.convert(conn, NY)
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", plain) == "2026-11-13T19:26:00.000000Z"
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", edited) == "2026-11-14T19:00:00.000000Z"


def test_typed_install_moments_are_converted_and_recorded_ones_left_alone(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        part = components.create(conn, name="Chain", component_type="chain")
        typed = components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at="2025-02-27T00:00:00.000000Z",
        )
        recorded = components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2025-03-01T15:04:05.123456Z", removed_at=None,
        )
        typed_times.convert(conn, NY)
        assert components.get_period(conn, typed.id).installed_at == "2024-08-22T16:51:00.000000Z"  # EDT
        assert components.get_period(conn, typed.id).removed_at == "2025-02-27T05:00:00.000000Z"  # EST
        assert components.get_period(conn, recorded.id).installed_at == "2025-03-01T15:04:05.123456Z"
        assert components.get_period(conn, recorded.id).removed_at is None


def test_maintenance_entries_get_an_instant_and_keep_their_local_date_and_time(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        timed = _entry(conn, bike=bike, day="2026-11-16", time="21:00")
        untimed = _entry(conn, bike=bike, day="2026-11-16")
        typed_times.convert(conn, NY)
        t = maintenance_db.get_by_id(conn, timed)
        u = maintenance_db.get_by_id(conn, untimed)
    assert (t.performed_at, t.performed_time, t.performed_instant) == ("2026-11-16", "21:00", "2026-11-17T02:00:00.000000Z")
    assert (u.performed_at, u.performed_time, u.performed_instant) == ("2026-11-16", None, "2026-11-17T04:59:59.999999Z")
    assert t.mileage_at_service == u.mileage_at_service == 7.5


@pytest.mark.parametrize(
    "stored,expected",
    [
        (None, None),
        ("1970-01-01T00:00:00.000000Z", "1970-01-01T00:00:00.000000Z"),  # since tracking began
        ("2026-11-16T23:59:59.999999Z", "2026-11-17T04:59:59.999999Z"),  # from an untimed entry
        ("2026-11-16T17:00:00.000000Z", "2026-11-16T22:00:00.000000Z"),  # from a typed time
        ("2026-11-16T22:00:41.654321Z", "2026-11-16T22:00:41.654321Z"),  # recorded at the moment
    ],
)
def test_schedule_starting_points_are_converted_by_their_form(db_path, stored, expected):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        schedule_id = _schedule(conn, bike, stored)
        typed_times.convert(conn, NY)
        assert _value(conn, "SELECT baseline_at FROM maintenance_schedule WHERE id = ?", schedule_id) == expected
        assert _value(conn, "SELECT baseline_date FROM maintenance_schedule WHERE id = ?", schedule_id) == "2026-11-16"


def test_record_keeping_times_are_left_alone(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        entry = _entry(conn, bike=bike, day="2026-11-16")
        before = conn.execute("SELECT created_at, updated_at FROM maintenance_log_entry WHERE id = ?", (entry,)).fetchone()
        bike_times = conn.execute("SELECT created_at, updated_at FROM bike WHERE id = ?", (bike.id,)).fetchone()
        typed_times.convert(conn, NY)
        assert tuple(conn.execute("SELECT created_at, updated_at FROM maintenance_log_entry WHERE id = ?", (entry,)).fetchone()) == tuple(before)
        assert tuple(conn.execute("SELECT created_at, updated_at FROM bike WHERE id = ?", (bike.id,)).fetchone()) == tuple(bike_times)


def test_in_utc_nothing_moves(db_path):
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Road")
        ride = _manual(conn, bike, "2026-11-16T17:00:00.000000Z")
        entry = _entry(conn, bike=bike, day="2026-11-16", time="21:00")
        typed_times.convert(conn, "UTC")
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T17:00:00.000000Z"
        assert maintenance_db.get_by_id(conn, entry).performed_instant == "2026-11-16T21:00:00.000000Z"


# ------------------------------------------------ the data step: copy first, all or nothing, once


def _as_before_the_update(conn):
    """Make the database look like one from before 075, so the data step runs again."""
    conn.execute("DELETE FROM schema_version WHERE version = '0019_typed_times_utc'")


def _seed_old_database():
    with connection.get_connection() as conn:
        _account(conn)
        bike = bikes.create(conn, name="Road")
        ride = _manual(conn, bike, "2026-11-16T17:00:00.000000Z")
        entry = _entry(conn, bike=bike, day="2026-11-16", time="21:00")
        conn.execute("UPDATE maintenance_log_entry SET performed_instant = NULL")
        _as_before_the_update(conn)
    return ride, entry


def _copies(db_path):
    return sorted(p.name for p in db_path.parent.glob("bikemaint-before-075-*.db"))


def test_a_fresh_database_records_the_step_and_makes_no_copy(db_path):
    with connection.get_connection() as conn:
        versions = {r[0] for r in conn.execute("SELECT version FROM schema_version")}
    assert "0019_typed_times_utc" in versions
    assert _copies(db_path) == []


def test_the_update_copies_the_database_then_converts_once(db_path):
    ride, entry = _seed_old_database()

    connection.run_migrations()

    copies = _copies(db_path)
    assert len(copies) == 1
    old = sqlite3.connect(db_path.parent / copies[0])
    assert old.execute("SELECT occurred_at FROM ride_activity WHERE id = ?", (ride,)).fetchone()[0] == "2026-11-16T17:00:00.000000Z"
    old.close()
    with connection.get_connection() as conn:
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T22:00:00.000000Z"

    connection.run_migrations()  # SC-007: a second start changes nothing

    with connection.get_connection() as conn:
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T22:00:00.000000Z"
        assert maintenance_db.get_by_id(conn, entry).performed_instant == "2026-11-17T02:00:00.000000Z"
    assert len(_copies(db_path)) == 1


def test_a_failure_part_way_converts_nothing_and_runs_again_next_time(db_path, monkeypatch):
    ride, _ = _seed_old_database()

    def half_then_fail(conn):
        typed_times.convert_database(conn)
        raise RuntimeError("disk full")

    monkeypatch.setattr(connection, "DATA_STEPS", [("0019_typed_times_utc", half_then_fail, True)])
    with pytest.raises(RuntimeError):
        connection.run_migrations()
    with connection.get_connection() as conn:
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T17:00:00.000000Z"
        assert _value(conn, "SELECT COUNT(*) FROM schema_version WHERE version = '0019_typed_times_utc'") == 0

    monkeypatch.undo()
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    connection.run_migrations()
    with connection.get_connection() as conn:
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T22:00:00.000000Z"


def test_if_the_copy_cannot_be_written_nothing_is_converted(db_path, monkeypatch, caplog):
    ride, _ = _seed_old_database()
    monkeypatch.setattr(connection, "_copy_path", lambda: db_path.parent / "missing-folder" / "copy.db")

    with pytest.raises(RuntimeError, match="copy"):
        connection.run_migrations()

    assert "missing-folder" in caplog.text
    with connection.get_connection() as conn:
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", ride) == "2026-11-16T17:00:00.000000Z"


# ------------------------------------------------ FR-007 / SC-002: totals and histories are unchanged


def test_totals_period_figures_and_histories_are_the_same_after_the_update(db_path):
    """Values worked out by hand with the pre-075 rule (typed times as New York wall clock)."""
    from app.services import maintenance_service

    with connection.get_connection() as conn:
        _account(conn)
        bike = bikes.create(conn, name="Road")
        chain = components.create(conn, name="Chain", component_type="chain")
        link = components.create(conn, name="Link", component_type="chain")
        _strava(conn, bike, 1, "2024-08-22T16:41:10.000000Z", 22.1)  # 12:41PM EDT: before the install
        _strava(conn, bike, 2, "2024-08-24T12:32:00.000000Z", 25.7)  # inside
        _strava(conn, bike, 3, "2025-02-27T04:30:00.000000Z", 15.8)  # 11:30PM EST on the 26th: inside
        _strava(conn, bike, 4, "2025-02-27T05:30:00.000000Z", 5.0)  # 12:30AM EST on the 27th: after
        _manual(conn, bike, "2025-02-26T23:00:00.000000Z", 3.0)  # typed 11PM on the 26th: inside
        period = components.insert_period(
            conn, chain.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at="2025-02-27T00:00:00.000000Z",
        )
        components.insert_period(  # inside the chain from Sept 1, still there
            conn, link.id, parent_bike_id=None, parent_component_id=chain.id,
            installed_at="2024-09-01T00:00:00.000000Z", removed_at=None,
        )
        late = _entry(conn, part=chain, day="2025-02-26", time="23:45")  # while on the bike
        _entry(conn, part=chain, day="2025-02-27", time="00:30")  # after it came off
        whole_day = _entry(conn, part=chain, day="2025-02-26")
        conn.execute("UPDATE maintenance_log_entry SET performed_instant = NULL")
        _as_before_the_update(conn)
        mileage.recompute_bike_total_mileage(conn, bike.id)

    connection.run_migrations()
    with connection.get_connection() as conn:
        mileage.recompute_all_component_totals(conn)
        chain_total = mileage.recompute_component_total_mileage(conn, chain.id)
        link_total = mileage.recompute_component_total_mileage(conn, link.id)
        period_rides = sorted(r.distance_miles for r in mileage.list_rides_for_period(conn, components.get_period(conn, period.id)))
        bike_total = bikes.get_by_id(conn, bike.id).total_mileage
        saved = {e.id: e.mileage_at_service for e in maintenance_db.list_for_component(conn, chain.id)}

    assert chain_total == pytest.approx(25.7 + 15.8 + 3.0)
    assert link_total == pytest.approx(15.8 + 3.0)
    assert period_rides == [3.0, 15.8, 25.7]
    assert bike_total == pytest.approx(22.1 + 25.7 + 15.8 + 5.0 + 3.0)
    assert set(saved.values()) == {7.5}
    past = [r.entry.id for r in maintenance_service.list_for_bike_rows(bike.id)]
    assert sorted(past) == sorted([late, whole_day])
    assert [r.entry.performed_at for r in maintenance_service.list_for_bike_rows(bike.id)] == ["2025-02-26", "2025-02-26"]


# ------------------------------------------------ specs/076 US3: stored short years are repaired as 20yy

import logging  # noqa: E402

PADS = "21-04-18T04:56:02.000000Z"  # the live GRX pads value: 0021-04-18 00:00 New York LMT, unpadded on Linux


def _period(conn, installed_at, removed_at=None):
    bike = bikes.create(conn, name="Madone")
    part = components.create(conn, name="Pads", component_type="brake_pad")
    period = components.insert_period(conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
                                      installed_at="2021-01-01T00:00:00.000000Z", removed_at=None)
    conn.execute("UPDATE component_installation_period SET installed_at = ?, removed_at = ? WHERE id = ?",
                 (installed_at, removed_at, period.id))
    return bike, period.id


def test_a_short_install_year_is_read_back_as_typed_and_stored_as_20yy(db_path):
    with connection.get_connection() as conn:
        _account(conn)
        _, unpadded = _period(conn, PADS)
        _, padded = _period(conn, "0021-04-18T04:56:02.000000Z", removed_at="0021-05-01T04:56:02.000000Z")
        counts = typed_times.repair_short_years(conn, NY)
        rows = dict(((r[0], (r[1], r[2])) for r in conn.execute(
            "SELECT id, installed_at, removed_at FROM component_installation_period")))
    assert rows[unpadded] == ("2021-04-18T04:00:00.000000Z", None)  # midnight EDT
    assert rows[padded] == ("2021-04-18T04:00:00.000000Z", "2021-05-01T04:00:00.000000Z")
    assert counts["component_installation_period"] == 3  # values changed: two installs and one removal


def test_manual_rides_entries_and_schedule_starts_are_repaired_but_strava_rides_are_not(db_path):
    with connection.get_connection() as conn:
        _account(conn)
        bike, _ = _period(conn, "2021-01-01T05:00:00.000000Z")
        manual = _manual(conn, bike, "26-07-17T16:56:02.000000Z")  # noon LMT on 0026-07-17
        _strava(conn, bike, 9, "2026-07-17T16:00:00.000000Z")
        conn.execute("UPDATE ride_activity SET occurred_at = '26-07-17T16:56:02.000000Z' WHERE source = 'strava'")
        entry = maintenance_db.create(conn, bike_id=bike.id, component_id=None, description="Check",
                                      mileage_at_service=0, performed_at="0021-04-18", performed_time=None,
                                      performed_instant="21-04-19T04:56:01.999999Z")
        conn.execute(
            "INSERT INTO maintenance_schedule (bike_id, name, interval_days, baseline_mileage, baseline_date, created_at, updated_at, baseline_at)"
            " VALUES (?, 'Check', 30, 0, '2021-04-18', '2026-01-01T00:00:00.000000Z', '2026-01-01T00:00:00.000000Z', ?)",
            (bike.id, "21-04-19T04:56:01.999999Z"),
        )
        typed_times.repair_short_years(conn, NY)
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE id = ?", manual) == "2026-07-17T16:00:00.000000Z"
        assert _value(conn, "SELECT occurred_at FROM ride_activity WHERE source = 'strava'") == "26-07-17T16:56:02.000000Z"
        assert _value(conn, "SELECT performed_at FROM maintenance_log_entry WHERE id = ?", entry.id) == "2021-04-18"
        assert _value(conn, "SELECT performed_instant FROM maintenance_log_entry WHERE id = ?", entry.id) == "2021-04-19T03:59:59.999999Z"
        assert _value(conn, "SELECT baseline_at FROM maintenance_schedule") == "2021-04-19T03:59:59.999999Z"


def test_normal_values_are_untouched(db_path):
    with connection.get_connection() as conn:
        _account(conn)
        _, period_id = _period(conn, "2021-04-18T04:00:00.000000Z")
        before = conn.execute("SELECT * FROM component_installation_period").fetchall()
        counts = typed_times.repair_short_years(conn, NY)
        assert [tuple(r) for r in conn.execute("SELECT * FROM component_installation_period").fetchall()] == [tuple(r) for r in before]
    assert set(counts.values()) == {0}


def test_a_value_that_cannot_be_repaired_is_left_and_logged(db_path, caplog):
    with connection.get_connection() as conn:
        _account(conn)
        _, period_id = _period(conn, "21-02-30T05:00:00.000000Z")
        with caplog.at_level(logging.WARNING, logger="app.db.typed_times"):
            typed_times.repair_short_years(conn, NY)
        assert _value(conn, "SELECT installed_at FROM component_installation_period WHERE id = ?", period_id) == "21-02-30T05:00:00.000000Z"
    assert any("component_installation_period" in r.message and f"id={period_id}" in r.message for r in caplog.records)


# ------------------------------------------------ specs/076: the repair runs once, with no copy


def _snapshot(conn):
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name != 'schema_version'")]
    return {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY rowid")] for t in tables}


def test_the_repair_step_runs_once_and_makes_no_copy(db_path):
    with connection.get_connection() as conn:
        _account(conn)
        _, period_id = _period(conn, PADS)
        conn.execute("DELETE FROM schema_version WHERE version = '0020_four_digit_years'")

    connection.run_migrations()
    connection.run_migrations()

    with connection.get_connection() as conn:
        assert _value(conn, "SELECT installed_at FROM component_installation_period WHERE id = ?", period_id) == "2021-04-18T04:00:00.000000Z"
        assert _value(conn, "SELECT COUNT(*) FROM schema_version WHERE version = '0020_four_digit_years'") == 1
    assert list(db_path.parent.glob("*-before-*")) == []


def test_a_database_with_no_short_years_is_unchanged_by_the_update(db_path):
    """SC-004."""
    with connection.get_connection() as conn:
        _account(conn)
        bike, _ = _period(conn, "2021-04-18T04:00:00.000000Z")
        _manual(conn, bike, "2026-07-17T16:00:00.000000Z")
        _entry(conn, bike=bike, day="2026-11-16", time="21:00")
        conn.execute("DELETE FROM schema_version WHERE version = '0020_four_digit_years'")
        before = _snapshot(conn)

    connection.run_migrations()

    with connection.get_connection() as conn:
        assert _snapshot(conn) == before
