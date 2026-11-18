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
    with pytest.raises(ValueError, match="overlaps"):
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


def test_a_parts_history_lists_the_latest_period_first_after_moves(db_path):
    a = bike_service.create_bike(name="A")
    b = bike_service.create_bike(name="B")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=a.id)
    component_service.move_component(saddle.id, parent_bike_id=b.id)
    component_service.move_component(saddle.id)  # to storage

    rows = history.describe_history(saddle.id)

    assert [r["place"] for r in rows] == ["B", "A"]  # latest installed first
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


# ------------------------------------------------ specs/075: typed moments are stored in UTC


def test_typed_moments_are_read_in_the_saved_zone(db_path, new_york):
    assert history.moment("2026-11-16", "08:00") == "2026-11-16T13:00:00.000000Z"
    assert history.moment("2026-11-16", None) == "2026-11-16T05:00:00.000000Z"  # local midnight
    assert history.moment("2026-07-04", "08:00") == "2026-07-04T12:00:00.000000Z"  # EDT


def test_the_future_check_compares_instants(db_path):
    from datetime import datetime, timedelta, timezone

    def utc(minutes):
        return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    history.log_period(saddle.id, bike_id=bike.id, installed_at=utc(-120), removed_at=utc(-1))
    with pytest.raises(ValueError, match="future"):
        history.log_period(saddle.id, bike_id=bike.id, installed_at=utc(-300), removed_at=utc(60))


def test_an_overlap_names_local_dates(db_path, new_york):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    # 9 PM EST on Jan 10 to 9 PM EST on Jan 20: the next UTC day each time
    history.log_period(saddle.id, bike_id=bike.id, installed_at="2025-01-11T02:00:00.000000Z",
                       removed_at="2025-01-21T02:00:00.000000Z")
    with pytest.raises(ValueError, match=r"2025-01-10 to 2025-01-20"):
        history.log_period(saddle.id, bike_id=bike.id, installed_at="2025-01-15T12:00:00.000000Z",
                           removed_at="2025-01-25T12:00:00.000000Z")


def test_an_unchanged_edit_keeps_recorded_instants(db_path, new_york):
    bike = bike_service.create_bike(name="A")
    saddle = _saddle()
    period = history.log_period(saddle.id, bike_id=bike.id, installed_at="2025-01-11T02:00:41.123456Z",
                                removed_at="2025-01-21T02:00:07.000000Z")

    saved = history.update_period(period.id, bike_id=bike.id, installed_at=history.moment("2025-01-10", "21:00"),
                                  removed_at=history.moment("2025-01-20", "21:00"))
    moved = history.update_period(period.id, bike_id=bike.id, installed_at=history.moment("2025-01-10", "22:00"),
                                  removed_at=history.moment("2025-01-20", "21:00"))

    assert (saved.installed_at, saved.removed_at) == ("2025-01-11T02:00:41.123456Z", "2025-01-21T02:00:07.000000Z")
    assert (moved.installed_at, moved.removed_at) == ("2025-01-11T03:00:00.000000Z", "2025-01-21T02:00:07.000000Z")


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


def test_logging_a_period_without_a_removal_installs_the_part_now(db_path):
    # 022 FR-012: the part is in storage after its first period was ended; a second period with
    # no removal puts it back on the bike as of that moment.
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    first = history.describe_history(chain.id)[0]["period"]
    history.update_period(
        first.id, bike_id=bike.id, parent_component_id=None,
        installed_at="2026-01-01T00:00:00.000000Z", removed_at="2026-03-01T00:00:00.000000Z",
    )
    assert component_service.get_component(chain.id).parent_bike_id is None  # in storage

    history.log_period(
        chain.id, bike_id=bike.id, installed_at="2026-04-01T00:00:00.000000Z", removed_at=None
    )

    part = component_service.get_component(chain.id)
    assert part.parent_bike_id == bike.id
    rows = history.describe_history(chain.id)
    assert [(r["period"].installed_at[:10], r["period"].removed_at) for r in rows] == [
        ("2026-04-01", None), ("2026-01-01", "2026-03-01T00:00:00.000000Z"),
    ]


def test_an_open_logged_period_cannot_overlap_another(db_path):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)

    with pytest.raises(ValueError, match="overlaps"):
        history.log_period(
            chain.id, bike_id=bike.id, installed_at="2026-04-01T00:00:00.000000Z", removed_at=None
        )



def test_describe_history_miles_use_the_same_clock_as_mileage(tmp_path, monkeypatch):
    from app.db import accounts, bikes, components, connection, mileage
    from app.services import component_history_service

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn, strava_athlete_id=1, access_token="a", refresh_token="r", expires_at="2099-01-01T00:00:00Z"
        )
        accounts.update_timezone(conn, account.id, "America/New_York")
        bike = bikes.create(conn, name="Madone")
        part = components.create(conn, name="Chain", component_type="chain")
        mileage.upsert_ride_activity(
            conn, strava_activity_id=1, strava_gear_id="g", bike_id=bike.id,
            distance_miles=22.1, occurred_at="2024-08-22T16:41:10.000000Z",  # 12:41PM EDT
        )
        components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T16:51:00.000000Z", removed_at="2025-02-27T05:00:00.000000Z",
        )
    rows = component_history_service.describe_history(part.id)
    assert rows[0]["miles"] == 0


# ------------------------------------------------ 015 FR-014 (branch 078): a still-installed period's place moves the part

T0 = "2020-08-30T14:21:00.000000Z"


def _open_period(component_id):
    periods = [p for p in history.list_history(component_id) if p.removed_at is None]
    assert len(periods) == 1
    return periods[0]


def test_changing_the_bike_of_a_still_installed_period_moves_the_part(db_path):
    bike_a = bike_service.create_bike(name="Madone 2.1")
    bike_b = bike_service.create_bike(name="Madone SLR7")
    groupset = component_service.create_component(
        name="Ultegra R8000", component_type="groupset", parent_bike_id=bike_a.id, installed_at=T0,
    )
    _ride(bike_a, 1, 10, "2021-05-01T08:00:00.000000Z")
    _ride(bike_b, 2, 25, "2021-06-01T08:00:00.000000Z")

    history.update_period(_open_period(groupset.id).id, bike_id=bike_b.id, installed_at=T0, removed_at=None)

    moved = component_service.get_component(groupset.id)
    assert (moved.parent_bike_id, moved.parent_component_id) == (bike_b.id, None)
    assert [(p.parent_bike_id, p.installed_at, p.removed_at) for p in history.list_history(groupset.id)] == [
        (bike_b.id, T0, None)
    ]
    assert _miles(groupset.id) == 25
    assert [c.id for c in component_service.get_tree_for_bike(bike_b.id)] == [groupset.id]
    assert component_service.get_tree_for_bike(bike_a.id) == []


def test_parts_inside_a_moved_part_follow_it_with_their_own_install_dates(db_path):
    bike_a = bike_service.create_bike(name="A")
    bike_b = bike_service.create_bike(name="B")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike_a.id, installed_at=T0)
    tire_at = "2022-01-10T12:00:00.000000Z"
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id, installed_at=tire_at)
    _ride(bike_a, 1, 10, "2023-05-01T08:00:00.000000Z")
    _ride(bike_b, 2, 25, "2023-06-01T08:00:00.000000Z")

    history.update_period(_open_period(wheel.id).id, bike_id=bike_b.id, installed_at=T0, removed_at=None)

    assert component_service.get_component(tire.id).parent_component_id == wheel.id
    tire_period = _open_period(tire.id)
    assert (tire_period.parent_bike_id, tire_period.parent_component_id, tire_period.installed_at) == (bike_b.id, wheel.id, tire_at)
    assert len(history.list_history(tire.id)) == 1
    assert _miles(tire.id) == 25 and _miles(wheel.id) == 25


def test_choosing_an_inside_part_records_the_bike_that_part_is_on(db_path):
    bike_a = bike_service.create_bike(name="A")
    bike_b = bike_service.create_bike(name="B")
    drivetrain = component_service.create_component(name="Drivetrain", component_type="drivetrain", parent_bike_id=bike_b.id, installed_at=T0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike_a.id, installed_at=T0)
    _ride(bike_b, 1, 25, "2023-06-01T08:00:00.000000Z")

    history.update_period(
        _open_period(chain.id).id, bike_id=bike_a.id, parent_component_id=drivetrain.id, installed_at=T0, removed_at=None,
    )

    moved = component_service.get_component(chain.id)
    assert (moved.parent_bike_id, moved.parent_component_id) == (None, drivetrain.id)
    period = _open_period(chain.id)
    assert (period.parent_bike_id, period.parent_component_id) == (bike_b.id, drivetrain.id)
    assert _miles(chain.id) == 25


def test_an_inside_part_in_storage_records_no_bike(db_path):
    bike_a = bike_service.create_bike(name="A")
    box = component_service.create_component(name="Spare wheel", component_type="wheel")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike_a.id, installed_at=T0)
    _ride(bike_a, 1, 10, "2023-06-01T08:00:00.000000Z")

    history.update_period(
        _open_period(chain.id).id, bike_id=bike_a.id, parent_component_id=box.id, installed_at=T0, removed_at=None,
    )

    assert component_service.get_component(chain.id).parent_component_id == box.id
    assert _open_period(chain.id).parent_bike_id is None
    assert _miles(chain.id) == 0


def test_a_part_cannot_be_moved_into_its_own_inside_part_by_an_edit(db_path):
    bike_a = bike_service.create_bike(name="A")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike_a.id, installed_at=T0)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id, installed_at=T0)
    before = _open_period(wheel.id)

    with pytest.raises(ValueError, match="sub-tree"):
        history.update_period(before.id, bike_id=bike_a.id, parent_component_id=tire.id, installed_at=T0, removed_at=None)

    assert component_service.get_component(wheel.id).parent_bike_id == bike_a.id
    assert _open_period(wheel.id) == before
