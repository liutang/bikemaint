"""The ride log screens (specs/006, M3)."""

import re

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_service, ride_service


def _bike(name="Road Bike", baseline=100.0):
    return bike_service.create_bike(name=name, manual_baseline_mileage=baseline)


def _strava(bike, activity_id, miles, when="2026-09-01T08:00:00.000000Z"):
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=activity_id, strava_gear_id="g", bike_id=bike.id,
            distance_miles=miles, occurred_at=when,
        )
        mileage_db.recompute_bike_total_mileage(conn, bike.id)


def _form(**kw):
    return {"ride_date": "2026-09-02", "ride_time": "07:30", "miles": "12.5", "note": "Loop", **kw}


def _total(bike):
    return bike_service.get_bike(bike.id).total_mileage


def _rows(html):
    return re.findall(r"<tr[^>]*>.*?</tr>", html.split("<tbody>")[1], re.S)


@pytest.mark.parametrize(
    "method,path",
    [("get", "/bikes/1/rides"), ("get", "/bikes/1/rides/new"), ("post", "/bikes/1/rides"),
     ("get", "/rides/1/edit"), ("post", "/rides/1"), ("post", "/rides/1/delete"), ("get", "/components/1/rides")],
)
def test_ride_routes_require_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_missing_bike_ride_or_part_is_a_404(signed_in_client):
    assert signed_in_client.get("/bikes/99/rides").status_code == 404
    assert signed_in_client.get("/bikes/99/rides/new").status_code == 404
    assert signed_in_client.post("/bikes/99/rides", data=_form()).status_code == 404
    assert signed_in_client.get("/rides/99/edit").status_code == 404
    assert signed_in_client.post("/rides/99", data=_form(bike_id="1")).status_code == 404
    assert signed_in_client.post("/rides/99/delete").status_code == 404
    assert signed_in_client.get("/components/99/rides").status_code == 404


# ---------------------------------------------------------------- the log


def test_the_log_starts_with_the_starting_mileage_then_shows_rides_newest_first(signed_in_client):
    bike = _bike(baseline=100)
    _strava(bike, 1, 10, "2026-09-01T08:00:00.000000Z")
    ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time="07:30", miles=5.5, note="Commute")

    html = signed_in_client.get(f"/bikes/{bike.id}/rides").text
    rows = _rows(html)

    assert "Starting mileage" in rows[-1] and "100.0" in rows[-1]
    assert "5.5" in rows[0] and "Commute" in rows[0] and "Manual" in rows[0] and "115.5" in rows[0]
    assert "10.0" in rows[1] and "Strava" in rows[1] and "110.0" in rows[1]
    assert "115.5 mi" in html  # the total
    assert re.search(r"<h1[^>]*>\s*Rides\s*</h1>", html)


def test_the_log_has_breadcrumbs_and_an_add_button(signed_in_client):
    bike = _bike("Trek Domane")

    html = signed_in_client.get(f"/bikes/{bike.id}/rides").text

    crumbs = re.search(r'<nav class="breadcrumb".*?</nav>', html, re.S).group(0)
    assert '<a href="/">Garage</a>' in crumbs and f'<a href="/bikes/{bike.id}">Trek Domane</a>' in crumbs
    assert 'aria-current="page"><span>Rides</span>' in crumbs
    assert f'href="/bikes/{bike.id}/rides/new"' in html


def test_strava_ride_times_are_converted_to_local_time_and_manual_ones_shown_as_typed(signed_in_client):
    bike = _bike()
    _strava(bike, 1, 10)
    ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time="07:30", miles=5, note=None)

    rows = _rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)

    assert "2026-09-02 7:30AM" in rows[0] and "<time" not in rows[0]
    assert '<time datetime="2026-09-01T08:00:00.000000Z">2026-09-01 8:00AM UTC</time>' in rows[1]


def test_strava_ride_times_follow_the_chosen_time_zone(signed_in_client):
    from app.db import accounts
    from app.services import settings_service

    with connection.get_connection() as conn:
        account = accounts.get_singleton(conn)
    settings_service.set_timezone(account.id, "America/Los_Angeles")
    bike = _bike()
    _strava(bike, 1, 10, when="2026-09-01T18:00:00.000000Z")
    ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time="07:30", miles=5, note=None)

    rows = _rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)

    assert "2026-09-01 11:00AM PDT" in rows[1]  # converted
    assert "2026-09-02 7:30AM" in rows[0] and "PDT" not in rows[0]  # typed: shown as typed
    assert "data-local" not in "".join(rows)


def test_every_ride_row_can_be_edited_or_deleted_and_the_start_row_has_no_link(signed_in_client):
    bike = _bike()
    _strava(bike, 1, 10)

    rows = _rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)

    assert "<a " not in rows[-1]  # specs/031: the baseline is edited on the Edit screen, not from here
    assert 'href="/rides/1/edit"' in rows[0] and 'action="/rides/1/delete"' in rows[0]


def test_adjustments_are_listed_but_read_only(signed_in_client):
    from app.services import sync_service

    bike = _bike(baseline=0)
    sync_service.adjust_bike_mileage(bike.id, delta_miles=-3, reason="Wrong ride")

    row = _rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)[0]

    assert "Adjustment" in row and "Wrong ride" in row and "-3.0" in row and "/edit" not in row


# ---------------------------------------------------------------- add


def test_the_add_form_has_date_time_miles_and_a_note(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}/rides/new").text

    for name, kind in (("ride_date", "date"), ("ride_time", "time"), ("miles", "number"), ("note", "text")):
        assert re.search(rf'<input id="{name}" name="{name}" type="{kind}"', html)
    assert 'name="bike_id"' not in html  # a new ride is for this bike
    assert re.search(r"<input id=\"ride_date\"[^>]*required", html) and re.search(r"<input id=\"miles\"[^>]*required", html)


def test_adding_a_ride_updates_the_mileage_and_returns_to_the_log(signed_in_client):
    bike = _bike(baseline=0)

    response = signed_in_client.post(f"/bikes/{bike.id}/rides", data=_form(), follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/rides"
    assert _total(bike) == 12.5
    assert "Loop" in signed_in_client.get(f"/bikes/{bike.id}/rides").text


@pytest.mark.parametrize(
    "change,field",
    [
        ({"miles": "0"}, "miles"), ({"miles": "-3"}, "miles"), ({"miles": "abc"}, "miles"),
        ({"miles": "5001"}, "miles"), ({"miles": ""}, "miles"),
        ({"ride_date": ""}, "ride_date"), ({"ride_date": "not-a-date"}, "ride_date"),
        ({"ride_time": "25:00"}, "ride_time"), ({"note": "x" * 201}, "note"),
    ],
)
def test_invalid_ride_entries_are_rejected_beside_the_field_keeping_the_rest(signed_in_client, change, field):
    bike = _bike(baseline=0)

    response = signed_in_client.post(f"/bikes/{bike.id}/rides", data=_form(**change))

    assert response.status_code == 422 and f'id="{field}-error"' in response.text
    assert _total(bike) == 0
    if field != "note":
        assert 'value="Loop"' in response.text


# ---------------------------------------------------------------- edit / re-assign


def test_the_edit_form_is_prefilled_and_offers_every_bike(signed_in_client):
    one = _bike("One")
    _bike("Two")
    ride = ride_service.create_ride(one.id, day=__import__("datetime").date(2026, 9, 2), time="07:30", miles=12.5, note="Loop")

    html = signed_in_client.get(f"/rides/{ride.id}/edit").text

    assert 'value="2026-09-02"' in html and 'value="07:30"' in html and 'value="12.5"' in html and 'value="Loop"' in html
    select = re.search(r'<select id="bike_id".*?</select>', html, re.S).group(0)
    assert re.findall(r'<option value="(\d+)"( selected)?', select) == [("1", " selected"), ("2", "")]


def test_editing_miles_and_date_updates_the_log_and_totals(signed_in_client):
    bike = _bike(baseline=0)
    ride = ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note=None)

    response = signed_in_client.post(
        f"/rides/{ride.id}", data=_form(bike_id=str(bike.id), miles="14", ride_date="2026-09-05"), follow_redirects=False
    )

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/rides"
    assert _total(bike) == 14
    assert "2026-09-05" in signed_in_client.get(f"/bikes/{bike.id}/rides").text


def test_reassigning_a_ride_moves_it_and_lands_on_the_new_bikes_log(signed_in_client):
    one = _bike("One", baseline=0)
    two = _bike("Two", baseline=0)
    ride = ride_service.create_ride(one.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note=None)

    response = signed_in_client.post(f"/rides/{ride.id}", data=_form(bike_id=str(two.id), miles="10"), follow_redirects=False)

    assert response.headers["location"] == f"/bikes/{two.id}/rides"
    assert (_total(one), _total(two)) == (0, 10)


def test_editing_a_strava_ride_survives_a_resync(signed_in_client):
    bike = _bike(baseline=0)
    _strava(bike, 1, 20)
    signed_in_client.post("/rides/1", data=_form(bike_id=str(bike.id), miles="18", ride_date="2026-09-01", ride_time="08:00"))

    _strava(bike, 1, 21)

    assert _total(bike) == 18


@pytest.mark.parametrize("bike_id", ["", "abc", "999", "-1"])
def test_a_bad_target_bike_is_rejected(signed_in_client, bike_id):
    bike = _bike(baseline=0)
    ride = ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note=None)

    response = signed_in_client.post(f"/rides/{ride.id}", data=_form(bike_id=bike_id))

    assert response.status_code == 422 and _total(bike) == 10


def test_an_invalid_edit_keeps_the_original_ride(signed_in_client):
    bike = _bike(baseline=0)
    ride = ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note=None)

    response = signed_in_client.post(f"/rides/{ride.id}", data=_form(bike_id=str(bike.id), miles="-1"))

    assert response.status_code == 422 and 'id="miles-error"' in response.text and _total(bike) == 10


# ---------------------------------------------------------------- delete


def test_deleting_a_ride_removes_it_and_reduces_the_mileage(signed_in_client):
    bike = _bike(baseline=50)
    ride = ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note=None)

    response = signed_in_client.post(f"/rides/{ride.id}/delete", follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == f"/bikes/{bike.id}/rides"
    assert _total(bike) == 50 and len(_rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)) == 1


def test_a_deleted_strava_ride_stays_deleted_after_a_sync(signed_in_client):
    bike = _bike(baseline=0)
    _strava(bike, 1, 10)

    signed_in_client.post("/rides/1/delete")
    _strava(bike, 1, 10)

    assert _total(bike) == 0 and len(_rows(signed_in_client.get(f"/bikes/{bike.id}/rides").text)) == 1


# ---------------------------------------------------------------- the Rides button and parts


def test_rides_replaces_adjust_mileage_on_bikes_and_parts(signed_in_client):
    bike = _bike()
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)

    bike_page = signed_in_client.get(f"/bikes/{bike.id}").text
    part_page = signed_in_client.get(f"/components/{wheel.id}").text

    assert f'href="/bikes/{bike.id}/rides">Rides</a>' in bike_page and "Adjust mileage" not in bike_page
    assert f'href="/components/{wheel.id}/rides">Rides</a>' in part_page and "Adjust mileage" not in part_page


def test_a_parts_ride_log_is_read_only_and_starts_with_its_baseline(signed_in_client):
    bike = _bike("Road Bike", baseline=0)
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id, manual_baseline_mileage=40)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2000-01-01T00:00:00.000000Z'")
    ride_service.create_ride(bike.id, day=__import__("datetime").date(2026, 9, 2), time=None, miles=10, note="Loop")

    html = signed_in_client.get(f"/components/{chain.id}/rides").text
    rows = _rows(html)

    assert "Starting mileage" in rows[-1] and "40.0" in rows[-1]
    assert "Loop" in rows[0] and "Road Bike" in rows[0] and "50.0" in rows[0]
    assert not re.search(r"/rides/\d+/(edit|delete)", html)  # no per-ride controls
    assert "Add a ride" not in html and "read-only" in html.lower()
    crumbs = re.search(r'<nav class="breadcrumb".*?</nav>', html, re.S).group(0)
    assert 'aria-current="page"><span>Rides</span>' in crumbs and f'/components/{chain.id}">Chain' in crumbs


def test_the_old_adjust_mileage_pages_still_work_for_existing_links(signed_in_client):
    bike = _bike()

    assert signed_in_client.get(f"/bikes/{bike.id}/mileage/adjust").status_code == 200


# ------------------------------------------------ specs/031: no redundant starting mileage link


def test_the_starting_row_stays_but_has_no_edit_link_on_a_bike(signed_in_client):
    bike = _bike(baseline=100.0)

    html = signed_in_client.get(f"/bikes/{bike.id}/rides").text

    assert "Starting mileage" in html and "100.0" in html and "Baseline" in html
    assert "Edit starting mileage" not in html


def test_the_starting_row_stays_but_has_no_edit_link_on_a_part(signed_in_client):
    bike = _bike()
    chain = component_service.create_component(
        name="Chain", component_type="chain", parent_bike_id=bike.id, manual_baseline_mileage=40.0
    )

    html = signed_in_client.get(f"/components/{chain.id}/rides").text

    assert "Starting mileage" in html and "40.0" in html
    assert "Edit starting mileage" not in html


def test_the_baseline_is_still_edited_on_the_edit_screens(signed_in_client):
    bike = _bike()
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)

    assert 'name="manual_baseline_mileage"' in signed_in_client.get(f"/bikes/{bike.id}/edit").text
    assert 'name="manual_baseline_mileage"' in signed_in_client.get(f"/components/{chain.id}/edit").text


def test_the_ride_form_offers_a_moving_time_and_the_log_shows_it(signed_in_client):
    # 039 FR-003, FR-004
    bike = _bike()
    assert 'name="moving_time"' in signed_in_client.get(f"/bikes/{bike.id}/rides/new").text

    response = signed_in_client.post(f"/bikes/{bike.id}/rides", data=_form(moving_time="1:30"), follow_redirects=False)

    assert response.status_code == 303
    html = signed_in_client.get(f"/bikes/{bike.id}/rides").text
    assert "Moving time" in html and "1:30" in _rows(html)[0]
    edit = signed_in_client.get(re.search(r'href="(/rides/\d+/edit)"', html).group(1)).text
    assert 'value="1:30"' in edit


@pytest.mark.parametrize("bad", ["abc", "1:75", "0:00"])
def test_a_bad_moving_time_is_refused_beside_the_field(signed_in_client, bad):
    bike = _bike()

    response = signed_in_client.post(f"/bikes/{bike.id}/rides", data=_form(moving_time=bad))

    assert response.status_code == 422 and 'id="moving_time-error"' in response.text
    assert len(ride_service.get_log_for_bike(bike.id).rows) == 1  # only the start row
