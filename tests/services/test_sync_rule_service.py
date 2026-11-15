"""Sync rules decide which Strava rides count (specs/060-sync-rules)."""

import pytest

from app.db import bikes, components, connection, mileage
from app.services import bike_service, component_service, ride_service, sync_rule_service, sync_service


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        bike = bikes.create(conn, name="Madone", manual_baseline_mileage=100)
        chain = components.create(conn, name="Chain", component_type="chain", parent_bike_id=bike.id)
        components.insert_period(
            conn, chain.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2020-01-01T00:00:00.000000Z", removed_at=None,
        )
        for n, miles, sport, rtype, name in (
            (1, 10, "Ride", "default", "Morning commute"),
            (2, 20, "Ride", "race", "Crit race"),
            (3, 30, "VirtualRide", "workout", "Zwift intervals"),
            (4, 40, None, None, None),  # imported before details were stored
        ):
            mileage.upsert_ride_activity(
                conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles,
                occurred_at=f"2024-06-0{n}T12:00:00.000000Z", sport_type=sport, ride_type=rtype, activity_name=name,
            )
        mileage.create_manual_ride(conn, bike_id=bike.id, distance_miles=5, occurred_at="2024-06-09T12:00:00.000000Z", note=None)
        mileage.recompute_bike_total_mileage(conn, bike.id)
        mileage.recompute_component_total_mileage(conn, chain.id)
    return bike, chain


def _bike_total(bike):
    return bike_service.get_bike(bike.id).total_mileage


def _chain_total(chain):
    return component_service.get_component(chain.id).total_mileage


def test_no_rule_counts_everything(world):
    bike, chain = world
    assert _bike_total(bike) == 205 and _chain_total(chain) == 105


def test_a_bike_rule_leaves_out_non_matching_strava_rides_but_not_manual_ones(world):
    bike, chain = world

    sync_rule_service.save_rule("bike", bike.id, sports=["Ride"], ride_types=["race"], keywords="")

    # race Ride (20) + unknown-details ride (40) + manual (5) + baseline (100)
    assert _bike_total(bike) == 165
    assert _chain_total(chain) == 65  # the part rides on the bike, so it follows
    miles = [row.miles for row in ride_service.get_log_for_bike(bike.id).rows if row.kind == "ride"]
    assert sorted(miles) == [5, 20, 40]


def test_keywords_match_the_name_and_clearing_brings_rides_back(world):
    bike, _ = world

    sync_rule_service.save_rule("bike", bike.id, sports=[], ride_types=[], keywords="commute, crit")
    assert _bike_total(bike) == 100 + 10 + 20 + 40 + 5  # commute, crit, unknown name, manual

    sync_rule_service.save_rule("bike", bike.id, sports=[], ride_types=[], keywords="")
    assert _bike_total(bike) == 205
    assert sync_rule_service.get_rule("bike", bike.id).keywords == ""


def test_an_edited_strava_ride_is_never_excluded(world):
    bike, _ = world
    with connection.get_connection() as conn:
        conn.execute("UPDATE ride_activity SET user_modified = 1 WHERE strava_activity_id = 3")

    sync_rule_service.save_rule("bike", bike.id, sports=["Ride"], ride_types=[], keywords="")

    assert _bike_total(bike) == 100 + 10 + 20 + 30 + 40 + 5  # only the untouched virtual ride would drop; it was edited


def test_a_part_rule_only_changes_that_parts_mileage(world):
    bike, chain = world

    sync_rule_service.save_rule("component", chain.id, sports=[], ride_types=["race"], keywords="")

    assert _chain_total(chain) == 20 + 40 + 5  # race ride, the unknown one and the manual ride
    assert _bike_total(bike) == 205  # the bike still counts every ride


def test_syncing_stores_the_details_and_applies_the_bike_rule(world):
    bike, _ = world
    sync_rule_service.save_rule("bike", bike.id, sports=["Ride"], ride_types=[], keywords="")
    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET strava_gear_id = 'g9'")
        sync_service._upsert_activities(conn, [
            {"id": 91, "gear_id": "g9", "distance": 16093.44, "start_date": "2024-07-01T12:00:00Z",
             "name": "Gravel grind", "sport_type": "GravelRide", "workout_type": 11},
            {"id": 92, "gear_id": "g9", "distance": 16093.44, "start_date": "2024-07-02T12:00:00Z",
             "name": "Road", "sport_type": "Ride", "workout_type": None},
        ])
        rows = {r["strava_activity_id"]: r for r in conn.execute("SELECT * FROM ride_activity WHERE strava_activity_id > 90")}

    assert (rows[91]["sport_type"], rows[91]["ride_type"], rows[91]["activity_name"]) == ("GravelRide", "race", "Gravel grind")
    assert rows[91]["filtered_out"] == 1 and rows[92]["filtered_out"] == 0 and rows[92]["ride_type"] == "default"


def test_bad_input_is_refused(world):
    bike, _ = world
    with pytest.raises(ValueError):
        sync_rule_service.save_rule("bike", bike.id, sports=["Swim"], ride_types=[], keywords="")
    with pytest.raises(ValueError):
        sync_rule_service.save_rule("bike", bike.id, sports=[], ride_types=["sprint"], keywords="")
    with pytest.raises(LookupError):
        sync_rule_service.save_rule("bike", 999, sports=[], ride_types=[], keywords="")
