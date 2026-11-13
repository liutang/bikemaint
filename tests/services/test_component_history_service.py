"""Manual parts history and install dates (specs/015-component-install-history)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_history_service as history, component_service


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    return path


def _ride(bike, activity_id, miles, when):
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=activity_id, strava_gear_id="g", bike_id=bike.id,
            distance_miles=miles, occurred_at=when,
        )


def _miles(component_id):
    return component_service.get_component(component_id).total_mileage


def _saddle():
    return component_service.create_component(name="Saddle", component_type="saddle")


def test_moment_defaults_and_formats():
    assert history.moment("2025-01-01", "08:30") == "2025-01-01T08:30:00.000000Z"
    assert history.moment("2025-01-01", None) == "2025-01-01T00:00:00.000000Z"
    assert history.moment(None, None).endswith("Z")
    with pytest.raises(ValueError):
        history.moment(None, "08:30")


def test_saddle_across_two_bikes_adds_each_window(db_path):
    bike_a = bike_service.create_bike(name="A")
    bike_b = bike_service.create_bike(name="B")
    saddle = _saddle()
    _ride(bike_a, 1, 10, "2024-12-15T08:00:00.000000Z")  # before install
    _ride(bike_a, 2, 20, "2025-03-01T08:00:00.000000Z")
    _ride(bike_a, 3, 30, "2025-08-01T08:00:00.000000Z")  # after removal
    _ride(bike_b, 4, 40, "2025-08-15T08:00:00.000000Z")  # between
    _ride(bike_b, 5, 50, "2025-10-01T08:00:00.000000Z")
    history.log_period(
        saddle.id, bike_id=bike_a.id, installed_at="2025-01-01T00:00:00.000000Z",
        removed_at="2025-07-01T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 20
    history.log_period(
        saddle.id, bike_id=bike_b.id, installed_at="2025-09-01T00:00:00.000000Z", removed_at="2025-12-01T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 70


def test_baseline_and_open_period_still_count(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = component_service.create_component(
        name="Saddle", component_type="saddle", manual_baseline_mileage=5
    )
    _ride(bike, 1, 7, "2025-02-01T08:00:00.000000Z")
    with connection.get_connection() as conn:
        from app.db import components as components_db

        components_db.set_parent(conn, saddle.id, parent_bike_id=bike.id, parent_component_id=None)
        components_db.open_installation_period(
            conn, saddle.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2025-01-01T00:00:00.000000Z",
        )
    history.recompute(saddle.id)
    assert _miles(saddle.id) == 12


def test_overlapping_period_is_rejected(db_path):
    bike = bike_service.create_bike(name="A")
    other = bike_service.create_bike(name="B")
    saddle = _saddle()
    history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-03-01T00:00:00.000000Z",
    )
    with pytest.raises(ValueError, match="overlap"):
        history.log_period(
            saddle.id, bike_id=other.id, installed_at="2025-02-01T00:00:00.000000Z",
            removed_at="2025-04-01T00:00:00.000000Z",
        )
    # touching ends are fine
    history.log_period(
        saddle.id, bike_id=other.id, installed_at="2025-03-01T00:00:00.000000Z", removed_at="2025-04-01T00:00:00.000000Z",
    )
    assert len(history.list_history(saddle.id)) == 2


def test_removal_must_follow_install_and_not_be_in_the_future(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    with pytest.raises(ValueError, match="after"):
        history.log_period(
            saddle.id, bike_id=bike.id, installed_at="2025-03-01T00:00:00.000000Z", removed_at="2025-03-01T00:00:00.000000Z",
        )
    future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:00.000000Z")
    with pytest.raises(ValueError, match="future"):
        history.log_period(
            saddle.id, bike_id=bike.id, installed_at="2025-03-01T00:00:00.000000Z", removed_at=future,
        )


def test_unknown_bike_parent_or_part_is_rejected(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    window = dict(installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-02-01T00:00:00.000000Z")
    with pytest.raises(LookupError):
        history.log_period(saddle.id, bike_id=99, **window)
    with pytest.raises(LookupError):
        history.log_period(saddle.id, bike_id=bike.id, parent_component_id=99, **window)
    with pytest.raises(LookupError):
        history.log_period(99, bike_id=bike.id, **window)


def test_update_period_recomputes_and_rechecks_overlap(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    _ride(bike, 2, 20, "2025-05-01T08:00:00.000000Z")
    first = history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-03-01T00:00:00.000000Z",
    )
    second = history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-04-01T00:00:00.000000Z", removed_at="2025-06-01T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 30
    history.update_period(
        first.id, bike_id=bike.id, installed_at="2025-03-01T00:00:00.000000Z", removed_at="2025-03-10T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 20
    with pytest.raises(ValueError, match="overlap"):
        history.update_period(
            second.id, bike_id=bike.id, installed_at="2025-03-05T00:00:00.000000Z", removed_at="2025-06-01T00:00:00.000000Z",
        )


def test_delete_period_recomputes(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    period = history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-03-01T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 10
    history.delete_period(period.id)
    assert _miles(saddle.id) == 0
    assert history.list_history(saddle.id) == []


def test_open_period_edit_changes_only_install_and_place(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = component_service.create_component(
        name="Saddle", component_type="saddle", parent_bike_id=bike.id
    )
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    open_period = history.list_history(saddle.id)[0]
    assert open_period.removed_at is None
    history.update_period(
        open_period.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at=None
    )
    assert _miles(saddle.id) == 10
    with pytest.raises(ValueError, match="removal"):
        history.log_period(
            saddle.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at=None
        )


def test_logging_and_deleting_a_period_leaves_no_maintenance_entries(db_path):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    from app.services import maintenance_service

    period = history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-01-01T08:30:00.000000Z", removed_at="2025-03-01T00:00:00.000000Z",
    )
    assert maintenance_service.list_for_component(saddle.id) == []
    assert maintenance_service.list_for_bike(bike.id) == []

    history.delete_period(period.id)
    assert maintenance_service.list_for_component(saddle.id) == []


def test_installed_at_on_create_backdates_and_counts_rides(db_path):
    bike = bike_service.create_bike(name="A")
    _ride(bike, 1, 10, "2025-01-15T08:00:00.000000Z")
    _ride(bike, 2, 5, "2025-03-15T08:00:00.000000Z")
    saddle = component_service.create_component(
        name="Saddle", component_type="saddle", parent_bike_id=bike.id,
        installed_at="2025-03-01T00:00:00.000000Z",
    )
    assert _miles(saddle.id) == 5


def test_installed_at_in_the_future_is_rejected_on_create(db_path):
    bike = bike_service.create_bike(name="A")
    future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:00.000000Z")
    with pytest.raises(ValueError, match="future"):
        component_service.create_component(
            name="Saddle", component_type="saddle", parent_bike_id=bike.id, installed_at=future
        )


# ------------------------------------------------ specs/022: a bike's install history


def test_a_parts_history_lists_each_period_in_order_after_moves(db_path):
    a = bike_service.create_bike(name="A")
    b = bike_service.create_bike(name="B")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=a.id)
    component_service.move_component(saddle.id, parent_bike_id=b.id)
    component_service.move_component(saddle.id)  # to storage

    rows = history.describe_history(saddle.id)

    assert [r["place"] for r in rows] == ["A", "B"]
    assert all(r["period"].removed_at for r in rows)


def test_bike_history_rows_describe_part_place_and_moments(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Front wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    saddle = component_service.create_component(name="Old saddle", component_type="saddle", parent_bike_id=bike.id)
    component_service.move_component(saddle.id)  # removed

    rows = history.describe_bike_history(bike.id)

    by_name = {r["component"].name: r for r in rows}
    assert by_name["Tire"]["place"] == "Front wheel" and by_name["Tire"]["kind_name"] == "Tire"
    assert by_name["Front wheel"]["place"] == "Road" and by_name["Front wheel"]["period"].removed_at is None
    assert by_name["Old saddle"]["period"].removed_at is not None and by_name["Old saddle"]["linked"] is True
    installed = [r["period"].installed_at for r in rows]
    assert installed == sorted(installed, reverse=True)
    assert tire.id


def test_a_part_moved_between_bikes_shows_on_each_bike(db_path):
    a = bike_service.create_bike(name="A")
    b = bike_service.create_bike(name="B")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=a.id)

    component_service.move_component(saddle.id, parent_bike_id=b.id)

    on_a = history.describe_bike_history(a.id)
    on_b = history.describe_bike_history(b.id)
    assert [(r["component"].name, r["period"].removed_at is not None) for r in on_a] == [("Saddle", True)]
    assert [(r["component"].name, r["period"].removed_at is None) for r in on_b] == [("Saddle", True)]


def test_a_deleted_part_and_a_deleted_parent_are_described_without_a_link(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)

    component_service.delete_component(saddle.id, keep_history=True)
    component_service.delete_component(wheel.id, confirmed=True, keep_history=True)  # the tire is kept, in storage

    by_name = {r["component"].name: r for r in history.describe_bike_history(bike.id)}
    assert by_name["Saddle"]["linked"] is False
    assert by_name["Tire"]["place"] == "a deleted part" and by_name["Tire"]["linked"] is True
    assert tire.id


# ------------------------------------------------ specs/023: the future check follows the time zone


def _in_zone(minutes_from_now, zone):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    wall = datetime.now(ZoneInfo(zone)).replace(tzinfo=None) + timedelta(minutes=minutes_from_now)
    return wall.strftime("%Y-%m-%dT%H:%M:00.000000Z")


def test_a_typed_moment_is_compared_with_the_current_time_in_the_chosen_zone(db_path):
    from app.db import accounts
    from app.services import settings_service

    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn, strava_athlete_id=1, access_token="a", refresh_token="r",
            expires_at="2099-01-01T00:00:00.000000Z",
        )
    settings_service.set_timezone(account.id, "Pacific/Auckland")  # many hours ahead of UTC
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()

    # an hour ago on the rider's clock is in the future by the UTC clock, yet it has passed here
    history.log_period(saddle.id, bike_id=bike.id, installed_at=_in_zone(-120, "Pacific/Auckland"),
                       removed_at=_in_zone(-60, "Pacific/Auckland"))
    with pytest.raises(ValueError, match="future"):
        history.log_period(saddle.id, bike_id=bike.id, installed_at=_in_zone(-300, "Pacific/Auckland"),
                           removed_at=_in_zone(60, "Pacific/Auckland"))


# ------------------------------------------------ specs/030: end an installation from the edit form


def _installed(bike, name="Saddle", kind="saddle", installed_at="2025-01-01T00:00:00.000000Z", **parent):
    part = component_service.create_component(
        name=name, component_type=kind, installed_at=installed_at, **({"parent_bike_id": bike.id} | parent)
    )
    return part, history.list_history(part.id)[-1]


def test_a_removed_moment_on_an_open_period_ends_it_and_moves_the_part_to_storage(db_path):
    bike = bike_service.create_bike(name="A")
    saddle, open_period = _installed(bike)
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    _ride(bike, 2, 20, "2025-06-01T08:00:00.000000Z")
    history.recompute(saddle.id)
    assert _miles(saddle.id) == 30

    history.update_period(
        open_period.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z",
        removed_at="2025-03-01T00:00:00.000000Z",
    )

    moved = component_service.get_component(saddle.id)
    assert (moved.parent_bike_id, moved.parent_component_id) == (None, None)  # in storage
    (period,) = history.list_history(saddle.id)
    assert period.removed_at == "2025-03-01T00:00:00.000000Z"
    assert _miles(saddle.id) == 10  # only the rides during the installation


def test_ending_an_installation_by_edit_writes_no_maintenance_entry(db_path):
    from app.services import maintenance_service

    bike = bike_service.create_bike(name="A")
    saddle, open_period = _installed(bike)

    history.update_period(open_period.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z",
                          removed_at="2025-03-01T00:00:00.000000Z")

    assert maintenance_service.list_for_component(saddle.id) == []
    assert maintenance_service.list_for_bike(bike.id) == []


def test_sub_parts_stay_inside_and_leave_the_bike_at_the_same_moment(db_path):
    bike = bike_service.create_bike(name="A")
    wheel, wheel_period = _installed(bike, "Wheel", "wheel")
    tire = component_service.create_component(
        name="Tire", component_type="tire", parent_component_id=wheel.id,
        installed_at="2025-01-01T00:00:00.000000Z",
    )
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    _ride(bike, 2, 20, "2025-06-01T08:00:00.000000Z")
    history.recompute(tire.id)

    history.update_period(wheel_period.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z",
                          removed_at="2025-03-01T00:00:00.000000Z")

    kept = component_service.get_component(tire.id)
    assert kept.parent_component_id == wheel.id and kept.parent_bike_id is None
    first, second = history.list_history(tire.id)
    assert first.removed_at == "2025-03-01T00:00:00.000000Z" and first.parent_bike_id == bike.id
    assert second.installed_at == "2025-03-01T00:00:00.000000Z" and second.parent_bike_id is None
    assert _miles(tire.id) == 10


def test_a_blank_removed_moment_leaves_the_part_installed(db_path):
    bike = bike_service.create_bike(name="A")
    saddle, open_period = _installed(bike)

    history.update_period(open_period.id, bike_id=bike.id, installed_at="2025-01-02T00:00:00.000000Z", removed_at=None)

    assert component_service.get_component(saddle.id).parent_bike_id == bike.id
    assert history.list_history(saddle.id)[0].removed_at is None


@pytest.mark.parametrize("removed", ["2025-01-01T00:00:00.000000Z", "2024-12-31T00:00:00.000000Z", "2999-01-01T00:00:00.000000Z"])
def test_a_removed_moment_that_is_not_possible_changes_nothing(db_path, removed):
    bike = bike_service.create_bike(name="A")
    saddle, open_period = _installed(bike)

    with pytest.raises(ValueError):
        history.update_period(open_period.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at=removed)

    assert component_service.get_component(saddle.id).parent_bike_id == bike.id
    assert history.list_history(saddle.id)[0].removed_at is None


# ------------------------------------------------ specs/031: places link to what still exists


def test_place_urls_point_at_existing_parts_and_bikes_only(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)

    assert history.describe_history(tire.id)[0]["place_url"] == f"/components/{wheel.id}"
    assert history.describe_history(saddle.id)[0]["place_url"] == f"/bikes/{bike.id}"
    rows = {r["component"].name: r for r in history.describe_bike_history(bike.id)}
    assert rows["Tire"]["place_url"] == f"/components/{wheel.id}"
    assert rows["Saddle"]["place_url"] == f"/bikes/{bike.id}"


def test_a_deleted_parent_or_a_deleted_bike_or_storage_has_no_link(db_path):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    component_service.delete_component(wheel.id, confirmed=True)  # the tire is kept, in storage

    (period, *_) = history.describe_history(tire.id)
    assert period["place"] == "a deleted part" and period["place_url"] is None

    spare = component_service.create_component(name="Spare", component_type="saddle")
    component_service.move_component(spare.id, parent_bike_id=bike.id)
    component_service.move_component(spare.id)  # back to storage
    bike_service.delete_bike(bike.id, confirmed=True)
    for row in history.describe_history(spare.id):
        assert row["place_url"] is None
