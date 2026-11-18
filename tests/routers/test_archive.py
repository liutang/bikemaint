"""Archive and unarchive screens and routes (specs/079 contracts/routes.md, ui-contract.md)."""

import re

import pytest

from app.db import bikes as bikes_db, connection
from app.services import archive_service, bike_service, component_service, schedule_service


def _schedule(**owner):
    schedule_service.create_schedule(service_type="Check", interval_kind="period", interval_value=1,
                                     interval_unit="months", **owner)


def _bike_with_parts(paired=True):
    bike = bike_service.create_bike(name="2014 Trek Madone 2.1")
    if paired:
        with connection.get_connection() as conn:
            bikes_db.set_strava_pairing(conn, bike.id, strava_gear_id="b9", strava_paired_at="2026-01-01T00:00:00.000000Z")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    _schedule(bike_id=bike.id)
    _schedule(bike_id=bike.id)
    _schedule(component_id=wheel.id)
    return bike


@pytest.mark.parametrize("path", ["/bikes/1/archive", "/bikes/1/unarchive", "/components/1/archive", "/components/1/unarchive"])
def test_archive_routes_require_sign_in(client, path):
    response = client.post(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_the_active_edit_screen_has_the_wide_archive_card_after_strava_and_delete(signed_in_client):
    bike = _bike_with_parts()
    page = signed_in_client.get(f"/bikes/{bike.id}/edit").text
    assert page.index('aria-labelledby="strava-heading"') < page.index('aria-labelledby="delete-heading"') < page.index('class="panel archive-card wide"')
    card = page[page.index('class="panel archive-card wide"'):]
    card = card[: card.index("</section>")]
    assert "Its 2 schedules are deleted." in card
    assert "It's unpaired from Strava. Imported rides are kept." in card
    assert "Its 2 parts" in card and "Their 1 schedule is deleted too." in card
    radios = re.findall(r'<input[^>]*name="attached"[^>]*>', card)
    assert len(radios) == 2 and all("required" in r and "checked" not in r for r in radios)
    assert {re.search(r'value="(\w+)"', r).group(1) for r in radios} == {"keep", "move"}
    assert "Archive bike</button>" in card


def test_a_bike_with_no_parts_has_no_choice(signed_in_client):
    bike = bike_service.create_bike(name="Lone")
    page = signed_in_client.get(f"/bikes/{bike.id}/edit").text
    card = page[page.index('class="panel archive-card"'):]  # beside Delete: no Strava card to span
    assert 'name="attached"' not in card[: card.index("</section>")]
    assert "It's unpaired from Strava" not in card[: card.index("</section>")]


def test_archiving_from_the_edit_screen_lands_on_the_garage_with_the_bike_under_archived(signed_in_client):
    bike = _bike_with_parts()
    response = signed_in_client.post(f"/bikes/{bike.id}/archive", data={"attached": "move"}, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/")

    garage = signed_in_client.get("/").text
    active = garage[garage.index('id="bike-list"'): garage.index("archived-section")]
    assert "2014 Trek Madone 2.1" not in active
    section = re.search(r'<details class="archived-section"( open)?>\s*<summary>Archived \(1\)</summary>(.*?)</details>', garage, re.S)
    assert section and section.group(1) is None
    assert "2014 Trek Madone 2.1" in section.group(2) and re.search(r'class="archived-on"[^>]*>.*Archived \d{4}-\d{2}-\d{2}', section.group(2), re.S)


def test_archiving_without_a_choice_is_refused_and_an_archived_bike_answers_409(signed_in_client):
    bike = _bike_with_parts()
    refused = signed_in_client.post(f"/bikes/{bike.id}/archive", data={})
    assert refused.status_code == 422 and "Choose whether to keep the parts" in refused.text
    assert bike_service.get_bike(bike.id).archived_at is None

    archive_service.archive_bike(bike.id, attached="keep")
    again = signed_in_client.post(f"/bikes/{bike.id}/archive", data={"attached": "keep"})
    assert again.status_code == 409


def test_no_archived_bikes_means_no_archived_section(signed_in_client):
    bike_service.create_bike(name="Active")
    assert "archived-section" not in signed_in_client.get("/").text


# ------------------------------------------------ US1: an archived bike refuses every change (FR-006)

from datetime import date  # noqa: E402

from app.db import mileage as mileage_db, schedules as schedules_db  # noqa: E402
from app.services import maintenance_service, ride_service  # noqa: E402


def _archived_bike_with_history():
    bike = bike_service.create_bike(name="Old Road")
    ride = ride_service.create_ride(bike.id, day=date(2026, 9, 2), time="07:30", miles=5, note=None)
    entry = maintenance_service.log_maintenance(bike_id=bike.id, description="Check", performed_at="2026-09-03")
    archive_service.archive_bike(bike.id, attached=None)
    return bike, ride, entry


def _requests(bike, ride, entry):
    return [
        (f"/bikes/{bike.id}", {"year": "2022", "make": "Trek", "model": "Domane", "category": "road"}),
        (f"/bikes/{bike.id}/rides", {"ride_date": "2026-09-05", "miles": "3"}),
        (f"/rides/{ride.id}", {"ride_date": "2026-09-02", "miles": "9", "bike_id": str(bike.id)}),
        (f"/rides/{ride.id}/delete", {}),
        (f"/bikes/{bike.id}/maintenance", {"service_type": "Check", "performed_at": "2026-09-04"}),
        (f"/maintenance/{entry.id}", {"service_type": "Clean", "performed_at": "2026-09-03"}),
        (f"/maintenance/{entry.id}/delete", {}),
        (f"/bikes/{bike.id}/schedules", {"service_type": "Check", "interval_kind": "period", "interval_value": "1",
                                         "interval_unit_period": "months", "interval_unit_usage": "miles"}),
        (f"/bikes/{bike.id}/mileage/adjust", {"delta_miles": "5"}),
        (f"/bikes/{bike.id}/sync-rules", {"sync_rules": "1", "keywords": "x"}),
        (f"/bikes/{bike.id}/strava-pairing", {"strava_gear_id": "b1"}),
        (f"/bikes/{bike.id}/strava-reimport", {}),
    ]


def _state(bike_id):
    with connection.get_connection() as conn:
        return (
            [tuple(r) for r in conn.execute("SELECT id, occurred_at, distance_miles, deleted_by_user FROM ride_activity ORDER BY id")],
            [tuple(r) for r in conn.execute("SELECT id, description, performed_at FROM maintenance_log_entry ORDER BY id")],
            len(schedules_db.list_active_for_bike(conn, bike_id)),
            tuple(conn.execute("SELECT name, total_mileage, strava_gear_id FROM bike WHERE id = ?", (bike_id,)).fetchone()),
            conn.execute("SELECT COUNT(*) FROM mileage_adjustment").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM sync_rule").fetchone()[0],
        )


def test_every_change_to_an_archived_bike_answers_409_and_changes_nothing(signed_in_client):
    bike, ride, entry = _archived_bike_with_history()
    before = _state(bike.id)
    for path, data in _requests(bike, ride, entry):
        response = signed_in_client.post(path, data=data, follow_redirects=False)
        assert response.status_code == 409, path
        assert "This bike is archived. Unarchive it to change it." in response.text, path
    assert _state(bike.id) == before


def test_a_ride_cannot_be_moved_onto_an_archived_bike(signed_in_client):
    old, _, _ = _archived_bike_with_history()
    active = bike_service.create_bike(name="New Road")
    ride = ride_service.create_ride(active.id, day=date(2026, 9, 2), time="08:00", miles=4, note=None)
    response = signed_in_client.post(f"/rides/{ride.id}", data={"ride_date": "2026-09-02", "miles": "4", "bike_id": str(old.id)})
    assert response.status_code == 409
    assert ride_service.get_ride(ride.id).bike_id == active.id


def test_an_archived_bikes_lists_have_no_change_controls(signed_in_client):
    bike, ride, entry = _archived_bike_with_history()
    rides = signed_in_client.get(f"/bikes/{bike.id}/rides").text
    assert "Add a ride" not in rides and f"/rides/{ride.id}/edit" not in rides and f"/rides/{ride.id}/delete" not in rides
    history = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text
    assert f"/maintenance/{entry.id}/edit" not in history and f"/maintenance/{entry.id}/delete" not in history
    assert f"/bikes/{bike.id}/maintenance/new" not in history


# ------------------------------------------------ US1: the archived bike's Edit and main screens


def test_the_archived_edit_screen_is_read_only_with_unarchive_beside_delete(signed_in_client):
    bike = _bike_with_parts()
    archive_service.archive_bike(bike.id, attached="keep")
    page = signed_in_client.get(f"/bikes/{bike.id}/edit").text
    assert re.search(r'class="archived-notice"[^>]*>.*Archived \d{4}-\d{2}-\d{2}\. Its details are locked\. Unarchive it below to change them\.', page, re.S)
    assert 'class="readonly-details"' in page
    assert ">Save</button>" not in page and 'name="sync_rules"' not in page
    assert 'class="panel unarchive-card"' in page and "Unarchive bike</button>" in page
    assert 'aria-labelledby="delete-heading"' in page
    assert "archive-card" not in page.replace("unarchive-card", "") and 'aria-labelledby="strava-heading"' not in page


def test_the_archived_bike_screen_offers_only_the_storage_drop(signed_in_client):
    bike = _bike_with_parts()
    archive_service.archive_bike(bike.id, attached="keep")
    page = signed_in_client.get(f"/bikes/{bike.id}").text
    assert "You can only take parts off to storage here. Unarchive it from its Edit screen." in page
    assert re.search(r'<div id="builder" class="builder" data-root="bike:\d+" data-locked>', page)
    assert 'class="palette-category"' not in page  # only the storage section is left
    assert "Nothing can be added to an archived bike." in page
    assert "storage-drop" in page
    assert "/builder/delete" not in page and "Trash " not in page
    assert "Add to…" not in page
    assert f'href="/bikes/{bike.id}/schedules"' not in page and "Pair with Strava" not in page
    assert "Garage Wheel (move to storage)" in page  # the keyboard way to take a part off stays
