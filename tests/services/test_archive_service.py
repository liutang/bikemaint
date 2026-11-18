"""Archiving bikes and parts (specs/079-archive-bikes-parts)."""

import pytest

from app.db import bikes as bikes_db, components as components_db, connection
from app.services import archive_service, bike_service, component_service

AT = "2026-11-18T15:00:00.000000Z"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.sqlite3"))
    connection.run_migrations()


def _archive_bike(bike_id):
    with connection.get_connection() as conn:
        bikes_db.set_archived(conn, bike_id, AT)


# ------------------------------------------------ the lock rule (research §1, §3)


def test_is_locked_follows_the_archived_tree(db_path):
    bike = bike_service.create_bike(name="2014 Trek Madone 2.1")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    spare = component_service.create_component(name="Spare", component_type="chain")
    assert not archive_service.is_locked("bike", bike.id)
    assert not archive_service.is_locked("component", wheel.id)

    _archive_bike(bike.id)

    assert archive_service.is_locked("bike", bike.id)
    assert archive_service.is_locked("component", wheel.id)
    assert not archive_service.is_locked("component", spare.id)


def test_require_unlocked_names_what_is_archived(db_path):
    bike = bike_service.create_bike(name="2014 Trek Madone 2.1")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    spare = component_service.create_component(name="Spare", component_type="chain")
    archive_service.require_unlocked("bike", bike.id)  # active: no error
    _archive_bike(bike.id)
    with connection.get_connection() as conn:
        components_db.set_archived(conn, spare.id, AT)

    with pytest.raises(archive_service.ArchivedError, match=r"^This bike is archived\. Unarchive it to change it\.$"):
        archive_service.require_unlocked("bike", bike.id)
    with pytest.raises(archive_service.ArchivedError, match=r"^This part is archived\. Unarchive it to change it\.$"):
        archive_service.require_unlocked("component", spare.id)
    with pytest.raises(
        archive_service.ArchivedError,
        match=r"^This part is on an archived bike, 2014 Trek Madone 2\.1\. Take it off to storage, or unarchive the bike\.$",
    ):
        archive_service.require_unlocked("component", wheel.id)


def test_a_part_inside_an_archived_part_names_that_part(db_path):
    box = component_service.create_component(name="Spare wheel", component_type="wheel")
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=box.id)
    with connection.get_connection() as conn:
        components_db.set_archived(conn, box.id, AT)
    with pytest.raises(
        archive_service.ArchivedError,
        match=r"^This part is inside an archived part, Spare wheel\. Take it off to storage, or unarchive that part\.$",
    ):
        archive_service.require_unlocked("component", tire.id)


# ------------------------------------------------ US1: archive a bike (research §4)

import logging  # noqa: E402

from app.db import mileage as mileage_db, schedules as schedules_db  # noqa: E402
from app.services import schedule_service  # noqa: E402


def _schedule(**owner):
    return schedule_service.create_schedule(
        service_type="Check", interval_kind="period", interval_value=1, interval_unit="months", **owner
    )


def _active_schedules():
    with connection.get_connection() as conn:
        return {(s.bike_id, s.component_id) for s in schedules_db.list_all_active(conn)}


def _setup():
    bike = bike_service.create_bike(name="2014 Trek Madone 2.1")
    with connection.get_connection() as conn:
        bikes_db.set_strava_pairing(conn, bike.id, strava_gear_id="b9", strava_paired_at=AT)
        mileage_db.upsert_ride_activity(conn, strava_activity_id=1, strava_gear_id="b9", bike_id=bike.id,
                                        distance_miles=10.0, occurred_at="2026-11-01T12:00:00.000000Z")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id,
                                               installed_at="2026-10-01T00:00:00.000000Z")
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id,
                                              installed_at="2026-10-01T00:00:00.000000Z")
    _schedule(bike_id=bike.id)
    _schedule(component_id=wheel.id)
    _schedule(component_id=tire.id)
    return bike, wheel, tire


def test_archiving_with_move_sends_parts_to_storage_with_their_sub_parts_and_schedules(db_path, caplog):
    bike, wheel, tire = _setup()

    with caplog.at_level(logging.INFO, logger="app.services.archive_service"):
        archive_service.archive_bike(bike.id, attached="move")

    archived = bike_service.get_bike(bike.id)
    assert archived.archived_at is not None and archived.strava_gear_id is None
    assert (component_service.get_component(wheel.id).parent_bike_id, component_service.get_component(wheel.id).parent_component_id) == (None, None)
    assert component_service.get_component(tire.id).parent_component_id == wheel.id
    assert _active_schedules() == {(None, wheel.id), (None, tire.id)}
    with connection.get_connection() as conn:
        assert len(mileage_db.list_rides_for_bike(conn, bike.id)) == 1
    assert component_service.get_component(wheel.id).total_mileage == 10.0
    assert "bike archived bike_id=%d schedules_deleted=1 attached=move parts_moved=1 unpaired=true" % bike.id in caplog.text


def test_archiving_with_keep_leaves_parts_on_and_turns_off_every_schedule(db_path):
    bike, wheel, tire = _setup()

    archive_service.archive_bike(bike.id, attached="keep")

    assert component_service.get_component(wheel.id).parent_bike_id == bike.id
    assert _active_schedules() == set()
    assert archive_service.is_locked("component", tire.id)


def test_archiving_a_bike_with_parts_needs_a_choice_and_an_archived_bike_cannot_be_archived_again(db_path):
    bike, _, _ = _setup()
    with pytest.raises(ValueError, match="Choose"):
        archive_service.archive_bike(bike.id, attached=None)
    assert bike_service.get_bike(bike.id).archived_at is None

    lone = bike_service.create_bike(name="Lone")
    archive_service.archive_bike(lone.id, attached=None)
    with pytest.raises(archive_service.ArchivedError):
        archive_service.archive_bike(lone.id, attached=None)
