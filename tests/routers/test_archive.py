"""Archive and unarchive screens and routes (specs/079 contracts/routes.md, ui-contract.md)."""

import html
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


# ------------------------------------------------ US2: take parts off an archived bike (FR-007)


def _kept():
    """An archived bike that kept a wheel holding a tire, plus an active bike and a stored chain."""
    bike = bike_service.create_bike(name="2014 Trek Madone 2.1")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id,
                                               installed_at="2026-01-01T00:00:00.000000Z")
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id,
                                              installed_at="2026-01-01T00:00:00.000000Z")
    archive_service.archive_bike(bike.id, attached="keep")
    other = bike_service.create_bike(name="New Road")
    chain = component_service.create_component(name="Chain", component_type="chain")
    return bike, wheel, tire, other, chain


def _place(component_id):
    c = component_service.get_component(component_id)
    return (c.parent_bike_id, c.parent_component_id)


def test_dragging_a_part_off_an_archived_bike_moves_it_to_storage_with_its_sub_parts(signed_in_client):
    bike, wheel, tire, _, _ = _kept()
    response = signed_in_client.post("/builder/move", data={"root": f"bike:{bike.id}", "component_id": wheel.id, "target": "storage"},
                                     headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert _place(wheel.id) == (None, None) and _place(tire.id) == (None, wheel.id)
    assert not archive_service.is_locked("component", wheel.id)


def test_the_old_move_route_can_take_a_part_off_too(signed_in_client):
    _, wheel, tire, _, _ = _kept()
    signed_in_client.post(f"/components/{wheel.id}/move", data={"target": "storage"})
    assert _place(wheel.id) == (None, None) and _place(tire.id) == (None, wheel.id)


@pytest.mark.parametrize("change", ["move_elsewhere", "move_within", "move_onto", "add_onto", "add_into", "delete_inside"])
def test_any_other_builder_change_on_an_archived_bike_answers_409(signed_in_client, change):
    bike, wheel, tire, other, chain = _kept()
    root = f"bike:{bike.id}"
    data = {
        "move_elsewhere": (f"/components/{wheel.id}/move", {"target": f"bike:{other.id}"}),
        "move_within": ("/builder/move", {"root": root, "component_id": tire.id, "target": f"bike:{bike.id}"}),
        "move_onto": (f"/components/{chain.id}/move", {"target": f"component:{wheel.id}"}),
        "add_onto": ("/builder/add", {"root": root, "component_type": "chain", "target": f"bike:{bike.id}"}),
        "add_into": ("/builder/add", {"root": root, "component_type": "tube", "target": f"component:{tire.id}"}),
        "delete_inside": ("/builder/delete", {"root": root, "component_id": tire.id, "confirmed": "true"}),
    }[change]
    before = {c: _place(c) for c in (wheel.id, tire.id, chain.id)}
    response = signed_in_client.post(data[0], data=data[1], headers={"HX-Request": "true"})
    assert response.status_code == 409
    assert "archived" in response.text
    if data[0].startswith("/builder"):
        assert 'id="builder"' in response.text
    assert {c: _place(c) for c in before} == before
    assert len(component_service.get_tree_for_bike(bike.id)) == 2


# ------------------------------------------------ US2: Install History of a locked item (FR-006, FR-007)

from app.services import component_history_service as history  # noqa: E402


def _open(component_id):
    return [p for p in history.list_history(component_id) if p.removed_at is None][0]


def test_ending_a_still_installed_row_on_an_archived_bike_back_dates_the_removal(signed_in_client):
    bike, wheel, tire, _, _ = _kept()
    period = _open(wheel.id)
    response = signed_in_client.post(f"/install-periods/{period.id}", data={
        "bike_id": str(bike.id), "installed_date": "2026-01-01", "installed_time": "00:00",
        "removed_date": "2026-03-01", "removed_time": "",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert _place(wheel.id) == (None, None) and _place(tire.id) == (None, wheel.id)
    assert history.get_period(period.id).removed_at.startswith("2026-03-01")


def test_other_period_changes_on_an_archived_bike_answer_409(signed_in_client):
    bike, wheel, _, other, chain = _kept()
    period = _open(wheel.id)
    base = {"installed_date": "2026-01-01", "installed_time": "00:00", "removed_date": "", "removed_time": ""}
    moved = signed_in_client.post(f"/install-periods/{period.id}", data={**base, "bike_id": str(other.id)})
    redated = signed_in_client.post(f"/install-periods/{period.id}", data={**base, "bike_id": str(bike.id), "installed_date": "2025-06-01"})
    logged = signed_in_client.post(f"/components/{chain.id}/install-history", data={
        "bike_id": str(bike.id), "installed_date": "2025-01-01", "removed_date": "2025-02-01"})
    assert (moved.status_code, redated.status_code, logged.status_code) == (409, 409, 409)
    assert history.get_period(period.id) == period and _place(wheel.id) == (bike.id, None)
    assert history.list_history(chain.id) == []


def test_a_closed_period_on_an_archived_bike_cannot_be_edited_or_deleted(signed_in_client):
    bike = bike_service.create_bike(name="Old")
    chain = component_service.create_component(name="Chain", component_type="chain")
    history.log_period(chain.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-02-01T00:00:00.000000Z")
    archive_service.archive_bike(bike.id, attached=None)
    period = history.list_history(chain.id)[0]
    edited = signed_in_client.post(f"/install-periods/{period.id}", data={
        "bike_id": str(bike.id), "installed_date": "2025-01-02", "removed_date": "2025-02-01"})
    deleted = signed_in_client.post(f"/install-periods/{period.id}/delete")
    assert (edited.status_code, deleted.status_code) == (409, 409)
    assert history.list_history(chain.id) == [period]
    page = signed_in_client.get(f"/components/{chain.id}/install-history").text
    assert f"/install-periods/{period.id}/edit" not in page and f"/install-periods/{period.id}/delete" not in page


def test_the_archived_bikes_install_history_and_period_form(signed_in_client):
    bike, wheel, _, _, _ = _kept()
    period = _open(wheel.id)
    page = signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    assert f"/bikes/{bike.id}/install-history/new" not in page
    assert f"/install-periods/{period.id}/edit" in page and f"/install-periods/{period.id}/delete" not in page
    form = signed_in_client.get(f"/install-periods/{period.id}/edit").text
    assert 'name="removed_date"' in form and 'type="hidden" name="bike_id"' in form
    assert '<select id="bike_id"' not in form and 'id="installed_date"' not in form


def test_locked_items_are_not_offered_as_places(signed_in_client):
    bike, wheel, tire, other, chain = _kept()
    options = [o["value"] for o in history.parent_options(chain.id)]
    assert str(wheel.id) not in options and str(tire.id) not in options
    form = signed_in_client.get(f"/components/{chain.id}/install-history/new").text
    assert f'value="{bike.id}"' not in form.split('name="bike_id"')[1].split("</select>")[0]


def test_every_change_to_a_part_kept_on_an_archived_bike_answers_409(signed_in_client):
    bike, wheel, tire, other, chain = _kept()
    with connection.get_connection() as conn:  # a schedule left on (as a part moved to storage would keep)
        schedules_db.create(conn, bike_id=None, component_id=wheel.id, name="Check", interval_miles=None, interval_days=30,
                            baseline_mileage=0, baseline_date="2026-01-01")
        schedule = schedules_db.list_active_for_component(conn, wheel.id)[0]
    requests = [
        ("/components", {"name": "Tube", "component_type": "tube", "parent_component_id": str(tire.id)}),
        (f"/components/{wheel.id}", {"name": "Renamed", "component_type": "wheel", "manual_baseline_mileage": "0"}),
        (f"/components/{wheel.id}/maintenance", {"service_type": "Check", "performed_at": "2026-09-04"}),
        (f"/components/{wheel.id}/mileage/adjust", {"delta_miles": "5"}),
        (f"/components/{wheel.id}/schedules", {"service_type": "Check", "interval_kind": "period", "interval_value": "1",
                                               "interval_unit_period": "months", "interval_unit_usage": "miles"}),
        (f"/schedules/{schedule.id}", {"service_type": "Check", "interval_kind": "period", "interval_value": "2",
                                       "interval_unit_period": "months", "interval_unit_usage": "miles"}),
        (f"/schedules/{schedule.id}/complete", {}),
        (f"/schedules/{schedule.id}/delete", {}),
        (f"/components/{wheel.id}/sync-rules", {"sync_rules": "1", "keywords": "x"}),
        (f"/components/{tire.id}/delete", {"confirmed": "true"}),
        (f"/bikes/{bike.id}/install-history", {"component_id": str(chain.id), "bike_id": str(bike.id),
                                                "installed_date": "2025-01-01", "removed_date": "2025-02-01"}),
        (f"/bikes/{bike.id}/strava-unpair", {}),
    ]
    for path, data in requests:
        response = signed_in_client.post(path, data=data, follow_redirects=False)
        assert response.status_code == 409, path
        assert "archived" in response.text, path
    assert component_service.get_component(wheel.id).name == "Wheel"
    assert component_service.get_component(tire.id) is not None
    with connection.get_connection() as conn:
        assert len(schedules_db.list_active_for_component(conn, wheel.id)) == 1
    assert [c.name for c in component_service.get_tree_for_bike(bike.id)] == ["Wheel", "Tire"]


# ------------------------------------------------ US3: archive a part; US4: unarchive


def test_an_installed_parts_edit_screen_says_to_take_it_off_first(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    page = signed_in_client.get(f"/components/{chain.id}/edit").text
    card = page[page.index("archive-card"):]
    card = card[: card.index("</section>")]
    assert "Take this part off to storage before archiving it." in card and "<button" not in card
    refused = signed_in_client.post(f"/components/{chain.id}/archive", data={})
    assert refused.status_code == 422 and component_service.get_component(chain.id).archived_at is None


def test_archiving_a_stored_part_lists_it_under_storage_archived_and_hides_it_from_pickers(signed_in_client):
    box = component_service.create_component(name="Spare wheel", component_type="wheel")
    component_service.create_component(name="Tire", component_type="tire", parent_component_id=box.id)
    page = signed_in_client.get(f"/components/{box.id}/edit").text
    assert 'name="attached"' in page and "Archive part</button>" in page and "Its 1 part" in page

    response = signed_in_client.post(f"/components/{box.id}/archive", data={"attached": "keep"}, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/components")

    storage = signed_in_client.get("/components").text
    section = re.search(r'<details class="archived-section">\s*<summary>Archived \(1\)</summary>(.*?)</details>', storage, re.S)
    assert section and "Spare wheel" in section.group(1) and "Archived " in section.group(1)
    assert "Spare wheel" not in storage[: storage.index("archived-section")]
    assert "Storage (0)" in signed_in_client.get("/").text
    bike = bike_service.create_bike(name="Road")
    screen = signed_in_client.get(f"/bikes/{bike.id}").text
    assert "In storage (0)" in screen and "Spare wheel" not in screen


def test_the_archived_parts_edit_screen_is_read_only_with_unarchive_and_delete(signed_in_client):
    spare = component_service.create_component(name="Spare", component_type="chain")
    archive_service.archive_part(spare.id, attached=None)
    page = signed_in_client.get(f"/components/{spare.id}/edit").text
    assert 'class="readonly-details"' in page and ">Save</button>" not in page
    assert "Unarchive part</button>" in page and f'action="/components/{spare.id}/delete"' in page


def test_unarchive_returns_to_an_editable_edit_screen(signed_in_client):
    bike = _bike_with_parts()
    archive_service.archive_bike(bike.id, attached="move")
    response = signed_in_client.post(f"/bikes/{bike.id}/unarchive", follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}/edit")
    page = signed_in_client.get(f"/bikes/{bike.id}/edit").text
    assert ">Save</button>" in page and "Archive bike</button>" in page
    assert "2014 Trek Madone 2.1" in signed_in_client.get("/").text.split("archived-section")[0]
    assert signed_in_client.post(f"/bikes/{bike.id}/unarchive").status_code == 409

    spare = component_service.create_component(name="Spare", component_type="chain")
    archive_service.archive_part(spare.id, attached=None)
    part = signed_in_client.post(f"/components/{spare.id}/unarchive", follow_redirects=False)
    assert (part.status_code, part.headers["location"]) == (303, f"/components/{spare.id}/edit")


def test_the_unarchive_card_wording(signed_in_client):
    bike = _bike_with_parts()
    archive_service.archive_bike(bike.id, attached="keep")
    page = signed_in_client.get(f"/bikes/{bike.id}/edit").text
    card = page[page.index('class="panel unarchive-card"'):]
    card = html.unescape(card[: card.index("</section>")])
    for text in ("Bring <strong>2014 Trek Madone 2.1</strong> back to the Garage's active bikes.",
                 "Its rides, details, sync rules, maintenance and parts can be changed again.",
                 "Its old schedules don't come back. Add new ones from its Schedules page.",
                 "It isn't paired with Strava. Pair it again to import its rides, including any from while it was archived."):
        assert text in card
