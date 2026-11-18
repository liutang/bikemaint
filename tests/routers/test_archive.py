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
