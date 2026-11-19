"""Ride log CRUD and running totals (specs/006, M3)."""

from datetime import date

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_service, ride_service, sync_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _bike(name="Road", baseline=100.0):
    return bike_service.create_bike(name=name, manual_baseline_mileage=baseline)


def _strava(bike, activity_id, miles, when):
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=activity_id, strava_gear_id="g", bike_id=bike.id,
            distance_miles=miles, occurred_at=when,
        )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)


def _total(bike):
    return bike_service.get_bike(bike.id).total_mileage


def test_the_log_starts_with_the_base_mileage_then_adds_rides(db_path):
    bike = _bike(baseline=100)
    _strava(bike, 1, 10, "2026-09-01T08:00:00.000000Z")
    ride_service.create_ride(bike.id, day=date(2026, 9, 2), time="07:30", miles=5.5, note="Commute")

    log = ride_service.get_log_for_bike(bike.id)

    assert [r.kind for r in log.rows] == ["ride", "ride", "start"]  # newest first, starting row last
    assert (log.rows[-1].miles, log.rows[-1].running_total) == (100, 100)
    assert [(r.miles, r.running_total, r.source) for r in log.rows[:-1]] == [(5.5, 115.5, "manual"), (10, 110, "strava")]
    assert log.total == 115.5 == _total(bike)


def test_rides_are_listed_newest_first_with_totals_computed_in_time_order(db_path):
    bike = _bike(baseline=0)
    ride_service.create_ride(bike.id, day=date(2026, 9, 3), time=None, miles=3, note=None)
    ride_service.create_ride(bike.id, day=date(2026, 9, 1), time=None, miles=1, note=None)
    ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=2, note=None)

    rides = [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"]

    assert [(r.miles, r.running_total) for r in rides] == [(3, 6), (2, 3), (1, 1)]


def test_creating_a_ride_updates_bike_and_part_mileage(db_path):
    bike = _bike(baseline=0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    # backdate the installation so the ride counts toward the chain
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2000-01-01T00:00:00.000000Z'")

    ride_service.create_ride(bike.id, day=date(2026, 9, 2), time="08:00", miles=12.5, note=None)

    assert _total(bike) == 12.5
    assert component_service.get_component(chain.id).total_mileage == 12.5


def test_manual_rides_are_stored_in_utc_with_a_noon_default(db_path):
    bike = _bike()

    a = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time="07:30", miles=1, note=None)
    b = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=1, note=None)

    assert a.occurred_at == "2026-09-02T07:30:00.000000Z" and b.occurred_at == "2026-09-02T12:00:00.000000Z"
    assert (a.source, a.user_modified) == ("manual", True)


def test_editing_miles_and_date_recalculates(db_path):
    bike = _bike(baseline=0)
    ride = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=10, note=None)

    ride_service.update_ride(ride.id, bike_id=bike.id, day=date(2026, 9, 5), time="18:15", miles=14, title="Hilly")

    (row,) = [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"]
    assert (row.miles, row.occurred_at, row.title) == (14, "2026-09-05T18:15:00.000000Z", "Hilly")  # specs/083
    assert _total(bike) == 14


def test_reassigning_a_ride_moves_the_mileage_between_bikes_and_their_parts(db_path):
    one = _bike("One", baseline=0)
    two = _bike("Two", baseline=0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=one.id)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2000-01-01T00:00:00.000000Z'")
    ride = ride_service.create_ride(one.id, day=date(2026, 9, 2), time=None, miles=20, note=None)
    assert component_service.get_component(chain.id).total_mileage == 20

    ride_service.update_ride(ride.id, bike_id=two.id, day=date(2026, 9, 2), time=None, miles=20, note=None)

    assert (_total(one), _total(two)) == (0, 20)
    assert component_service.get_component(chain.id).total_mileage == 0
    assert [r for r in ride_service.get_log_for_bike(one.id).rows if r.kind == "ride"] == []
    assert len([r for r in ride_service.get_log_for_bike(two.id).rows if r.kind == "ride"]) == 1


def test_a_part_that_moved_away_is_still_recalculated(db_path):
    one = _bike("One", baseline=0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=one.id)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2000-01-01T00:00:00.000000Z'")
    ride = ride_service.create_ride(one.id, day=date(2026, 9, 2), time=None, miles=20, note=None)
    component_service.move_component(chain.id)  # off the bike, to storage; it keeps the 20 miles
    assert component_service.get_component(chain.id).total_mileage == 20

    ride_service.update_ride(ride.id, bike_id=one.id, day=date(2026, 9, 2), time=None, miles=8, note=None)

    assert component_service.get_component(chain.id).total_mileage == 8  # not stale


def test_deleting_a_ride_reduces_the_mileage(db_path):
    bike = _bike(baseline=50)
    ride = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=10, note=None)

    ride_service.delete_ride(ride.id)

    assert _total(bike) == 50
    assert [r.kind for r in ride_service.get_log_for_bike(bike.id).rows] == ["start"]


def test_a_deleted_strava_ride_is_not_restored_by_the_next_sync(db_path):
    bike = _bike(baseline=0)
    _strava(bike, 1, 10, "2026-09-01T08:00:00.000000Z")
    (row,) = [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"]
    ride_service.delete_ride(row.id)

    _strava(bike, 1, 10, "2026-09-01T08:00:00.000000Z")  # the same activity arrives again

    assert _total(bike) == 0
    assert [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"] == []


def test_an_edited_strava_ride_keeps_the_riders_values_after_a_sync(db_path):
    bike = _bike(baseline=0)
    _strava(bike, 1, 20, "2026-09-01T08:00:00.000000Z")
    (row,) = [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"]
    ride_service.update_ride(row.id, bike_id=bike.id, day=date(2026, 9, 1), time="08:00", miles=18, note=None)

    _strava(bike, 1, 21, "2026-09-01T08:00:00.000000Z")
    with connection.get_connection() as conn:
        mileage_db.recompute_bike_total_mileage(conn, bike.id)

    assert _total(bike) == 18


def test_adjustments_still_count_and_show_in_the_log(db_path):
    bike = _bike(baseline=0)
    ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=10, note=None)
    sync_service.adjust_bike_mileage(bike.id, delta_miles=-3, reason="Wrong ride")

    log = ride_service.get_log_for_bike(bike.id)

    kinds = [r.kind for r in log.rows]
    assert kinds.count("adjustment") == 1
    adjustment = next(r for r in log.rows if r.kind == "adjustment")
    assert (adjustment.miles, adjustment.note, adjustment.editable) == (-3, "Wrong ride", False)
    assert log.total == 7 == _total(bike)


@pytest.mark.parametrize("miles", [0, -1, 5001])
def test_invalid_miles_are_refused(db_path, miles):
    bike = _bike()

    with pytest.raises(ValueError):
        ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=miles, note=None)
    assert [r for r in ride_service.get_log_for_bike(bike.id).rows if r.kind == "ride"] == []


def test_a_ride_for_a_missing_bike_or_a_missing_ride_raises(db_path):
    bike = _bike()
    with pytest.raises(LookupError):
        ride_service.create_ride(999, day=date(2026, 9, 2), time=None, miles=1, note=None)
    with pytest.raises(LookupError):
        ride_service.update_ride(999, bike_id=bike.id, day=date(2026, 9, 2), time=None, miles=1, note=None)
    with pytest.raises(LookupError):
        ride_service.delete_ride(999)
    ride = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=1, note=None)
    with pytest.raises(LookupError):
        ride_service.update_ride(ride.id, bike_id=999, day=date(2026, 9, 2), time=None, miles=1, note=None)


def test_a_deleted_bike_has_no_log(db_path):
    bike = _bike()
    bike_service.delete_bike(bike.id)

    with pytest.raises(LookupError):
        ride_service.get_log_for_bike(bike.id)


def test_a_parts_log_lists_the_rides_while_it_was_installed_read_only(db_path):
    bike = _bike("Road", baseline=0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id, manual_baseline_mileage=40)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2000-01-01T00:00:00.000000Z'")
    ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=10, note="Loop")
    ride_service.create_ride(bike.id, day=date(2026, 9, 3), time=None, miles=5, note=None)

    log = ride_service.get_log_for_component(chain.id)

    assert (log.rows[-1].kind, log.rows[-1].miles, log.rows[-1].running_total) == ("start", 40, 40)
    assert [(r.miles, r.running_total) for r in log.rows[:-1]] == [(5, 55), (10, 50)]
    assert all(not r.editable for r in log.rows) and log.rows[0].bike_name == "Road"
    assert log.total == 55 == component_service.get_component(chain.id).total_mileage


def test_a_part_never_ridden_has_just_its_starting_mileage(db_path):
    spare = component_service.create_component(name="Spare", component_type="saddle", manual_baseline_mileage=7)

    log = ride_service.get_log_for_component(spare.id)

    assert [(r.kind, r.miles) for r in log.rows] == [("start", 7)] and log.total == 7


def test_durations_parse_and_format_as_h_mm():
    assert ride_service.parse_duration("1:30") == 5400
    assert ride_service.parse_duration("0:45") == 2700
    assert ride_service.parse_duration("") is None and ride_service.parse_duration(None) is None
    assert ride_service.format_duration(5400) == "1:30"
    assert ride_service.format_duration(59 * 60 + 40) == "0:59"  # whole minutes, rounded down
    assert ride_service.format_duration(None) == ""


def test_a_manual_ride_keeps_its_moving_time_and_the_log_shows_it(db_path):
    bike = _bike()

    ride = ride_service.create_ride(
        bike.id, day=date(2026, 9, 2), time=None, miles=5, note=None, moving_seconds=5400
    )
    ride_service.update_ride(
        ride.id, bike_id=bike.id, day=date(2026, 9, 2), time=None, miles=5, note=None, moving_seconds=3600
    )

    (row, _start) = ride_service.get_log_for_bike(bike.id).rows
    assert row.moving_seconds == 3600


# ------------------------------------------------ specs/075: typed times are stored in UTC


def test_a_manual_ride_is_read_in_the_saved_zone_and_stored_in_utc(db_path, new_york):
    bike = _bike()

    evening = ride_service.create_ride(bike.id, day=date(2026, 11, 16), time="17:39", miles=1, note=None)
    noon = ride_service.create_ride(bike.id, day=date(2026, 11, 16), time=None, miles=1, note=None)
    summer = ride_service.create_ride(bike.id, day=date(2026, 7, 4), time="09:00", miles=1, note=None)

    assert evening.occurred_at == "2026-11-16T22:39:00.000000Z"  # 5:39 PM EST
    assert noon.occurred_at == "2026-11-16T17:00:00.000000Z"  # noon EST
    assert summer.occurred_at == "2026-07-04T13:00:00.000000Z"  # 9:00 AM EDT


def test_saving_a_ride_with_an_unchanged_date_and_time_keeps_its_instant(db_path, new_york):
    bike = _bike()
    _strava(bike, 7, 10, "2026-11-13T19:26:41.000000Z")  # 2:26:41 PM EST
    ride = ride_service.get_log_for_bike(bike.id).rows[0]

    kept = ride_service.update_ride(ride.id, bike_id=bike.id, day=date(2026, 11, 13), time="14:26", miles=12, note=None)
    moved = ride_service.update_ride(ride.id, bike_id=bike.id, day=date(2026, 11, 13), time="15:00", miles=12, note=None)

    assert kept.occurred_at == "2026-11-13T19:26:41.000000Z"
    assert moved.occurred_at == "2026-11-13T20:00:00.000000Z"


# ------------------------------------------------ specs/076 FR-011: a ride can't be dated in the future

from datetime import datetime, timezone  # noqa: E402

from app.db import accounts  # noqa: E402
from app.services import clock_service  # noqa: E402

FUTURE = "The ride date cannot be in the future."


@pytest.fixture
def ten_am_in_new_york(db_path, monkeypatch):
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(conn, strava_athlete_id=1, access_token="a", refresh_token="r",
                                              expires_at="2099-01-01T00:00:00Z")
        accounts.update_timezone(conn, account.id, "America/New_York")
    monkeypatch.setattr(clock_service, "_utc_now", lambda: datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc))


def test_a_ride_dated_tomorrow_or_later_today_is_refused(ten_am_in_new_york):
    bike = _bike()
    with pytest.raises(ValueError, match=FUTURE):
        ride_service.create_ride(bike.id, day=date(2026, 11, 19), time=None, miles=5, note=None)
    with pytest.raises(ValueError, match=FUTURE):
        ride_service.create_ride(bike.id, day=date(2026, 11, 18), time="11:00", miles=5, note=None)
    with connection.get_connection() as conn:
        assert mileage_db.list_rides_for_bike(conn, bike.id) == []


def test_a_ride_earlier_today_or_today_without_a_time_is_accepted(ten_am_in_new_york):
    bike = _bike()
    ride_service.create_ride(bike.id, day=date(2026, 11, 18), time="09:30", miles=5, note=None)
    ride_service.create_ride(bike.id, day=date(2026, 11, 18), time=None, miles=6, note=None)
    assert _total(bike) == 111


def test_editing_a_ride_into_the_future_is_refused_and_changes_nothing(ten_am_in_new_york):
    bike = _bike()
    ride = ride_service.create_ride(bike.id, day=date(2026, 11, 17), time="08:00", miles=5, note=None)
    with pytest.raises(ValueError, match=FUTURE):
        ride_service.update_ride(ride.id, bike_id=bike.id, day=date(2026, 12, 1), time=None, miles=5, note=None)
    assert ride_service.get_ride(ride.id).occurred_at == ride.occurred_at


def test_strava_rides_are_never_checked(ten_am_in_new_york):
    bike = _bike()
    _strava(bike, 1, 10, "2026-12-01T08:00:00.000000Z")
    assert _total(bike) == 110


# ------------------------------------------------ specs/083: titles; Strava titles and types are read-only


def _row(ride_id):
    with connection.get_connection() as conn:
        return tuple(conn.execute("SELECT activity_name, sport_type, note FROM ride_activity WHERE id = ?", (ride_id,)).fetchone())


def test_a_manual_ride_has_a_title_and_a_blank_title_saves_as_manual_ride(db_path):
    bike = _bike()
    trainer = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time=None, miles=5, note=None, title="Trainer")
    blank = ride_service.create_ride(bike.id, day=date(2026, 9, 3), time=None, miles=5, note=None, title="  ")
    assert _row(trainer.id) == ("Trainer", None, None)
    assert _row(blank.id) == ("Manual Ride", None, None)
    ride_service.update_ride(trainer.id, bike_id=bike.id, day=date(2026, 9, 2), time=None, miles=5, note=None, title="Rollers")
    assert _row(trainer.id) == ("Rollers", None, None)


def test_editing_a_strava_ride_changes_its_note_but_never_its_title_or_type(db_path):
    bike = _bike()
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(conn, strava_activity_id=77, strava_gear_id="g", bike_id=bike.id, distance_miles=10,
                                        occurred_at="2026-09-01T08:00:00.000000Z", sport_type="GravelRide", activity_name="Gravel loop")
        ride_id = conn.execute("SELECT id FROM ride_activity WHERE strava_activity_id = 77").fetchone()[0]
    ride_service.update_ride(ride_id, bike_id=bike.id, day=date(2026, 9, 1), time="08:00", miles=10,
                             note="Chain skipped", title="Renamed here")
    assert _row(ride_id) == ("Gravel loop", "GravelRide", "Chain skipped")
