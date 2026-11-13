import re

import pytest


@pytest.mark.parametrize(
    "method,path,data",
    [
        ("get", "/", None),
        ("get", "/bikes/1", None),
        ("get", "/bikes/new", None),
        ("post", "/bikes", {"year": "2022", "make": "Trek", "model": "Domane", "category": "road", "manual_baseline_mileage": "0"}),
        ("get", "/bikes/1/edit", None),
        ("post", "/bikes/1", {"year": "2022", "make": "Trek", "model": "Domane", "category": "road", "manual_baseline_mileage": "0"}),
        ("post", "/bikes/1/delete", {}),
    ],
)
def test_bike_routes_redirect_unauthenticated_requests_to_login(client, method, path, data):
    kwargs = {"data": data} if method == "post" else {}
    response = getattr(client, method)(path, follow_redirects=False, **kwargs)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _login(client, monkeypatch, athlete_id=42):
    from app.services import strava_client

    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 1893456000,
            "athlete": {"id": athlete_id},
        },
    )
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)


def test_garage_overview_lists_created_bikes(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"year": "2023", "make": "Canyon", "model": "Grizl", "category": "gravel"})
    response = client.get("/")

    assert response.status_code == 200
    assert "2023 Canyon Grizl" in response.text


def test_create_then_view_bike_detail(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"year": "2022", "make": "Trek", "model": "Domane", "category": "road", "manual_baseline_mileage": "10"})

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = '2022 Trek Domane'").fetchone()["id"]

    response = client.get(f"/bikes/{bike_id}")

    assert response.status_code == 200
    assert "2022 Trek Domane" in response.text


# ------------------------------------------------ specs/029: safe bike delete


def _bike_named(name="2023 Trek Madone"):
    from app.services import bike_service

    return bike_service.create_bike(name=name)


def test_the_main_screen_has_no_delete_control(signed_in_client):
    bike = _bike_named()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert "Delete this bike" not in html and "Delete bike" not in html
    assert f'action="/bikes/{bike.id}/delete"' not in html


def test_the_edit_screen_has_a_separate_delete_area_that_asks_for_the_full_name(signed_in_client):
    bike = _bike_named()

    html = signed_in_client.get(f"/bikes/{bike.id}/edit").text

    area = html.split('id="delete-heading"')[1]
    assert "Delete this bike" in html and "2023 Trek Madone" in area
    assert "move to storage" in area and "cannot be undone" in area
    assert f'action="/bikes/{bike.id}/delete"' in area
    assert re.search(r'<input[^>]*name="confirm_name"[^>]*required', area)
    assert 'pattern="2023 Trek Madone"' in area and 'autocomplete="off"' in area
    assert "btn-danger" in area


def test_the_pattern_is_escaped_for_names_with_punctuation(signed_in_client):
    bike = _bike_named("2023 Trek Madone SLR (Disc) 7.0")

    html = signed_in_client.get(f"/bikes/{bike.id}/edit").text

    assert r'pattern="2023 Trek Madone SLR \(Disc\) 7\.0"' in html


def test_the_new_bike_form_has_no_delete_area(signed_in_client):
    assert "Delete this bike" not in signed_in_client.get("/bikes/new").text


def test_deleting_with_the_exact_name_returns_to_the_garage_and_removes_the_bike(signed_in_client):
    from app.services import bike_service, component_service

    bike = _bike_named()
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)

    response = signed_in_client.post(
        f"/bikes/{bike.id}/delete", data={"confirm_name": "2023 Trek Madone"}, follow_redirects=False
    )

    assert (response.status_code, response.headers["location"]) == (303, "/")
    assert bike_service.get_bike(bike.id) is None
    assert component_service.get_component(saddle.id).parent_bike_id is None


@pytest.mark.parametrize("typed", [None, "", "2023 trek madone", " 2023 Trek Madone", "Trek"])
def test_a_missing_or_wrong_name_deletes_nothing_and_shows_the_edit_screen_with_a_message(signed_in_client, typed):
    from app.services import bike_service

    bike = _bike_named()
    data = {} if typed is None else {"confirm_name": typed}

    response = signed_in_client.post(f"/bikes/{bike.id}/delete", data=data)

    assert response.status_code == 422
    assert 'id="confirm_name-error"' in response.text and "full name" in response.text
    assert bike_service.get_bike(bike.id) is not None


def test_deleting_an_unknown_bike_is_a_404(signed_in_client):
    assert signed_in_client.post("/bikes/99/delete", data={"confirm_name": "x"}).status_code == 404


def test_an_old_confirmed_flag_no_longer_deletes(signed_in_client):
    from app.services import bike_service

    bike = _bike_named()

    response = signed_in_client.post(f"/bikes/{bike.id}/delete", data={"confirmed": "true"})

    assert response.status_code == 422 and bike_service.get_bike(bike.id) is not None


# ------------------------------------------------ year/make/model form (specs/005, M1)

import re  # noqa: E402

from app.services import bike_service  # noqa: E402

DOMANE = {"year": "2022", "make": "Trek", "model": "Domane", "category": "road"}


def test_add_form_has_text_entries_and_only_the_category_is_a_dropdown(signed_in_client):
    html = signed_in_client.get("/bikes/new").text

    for name in ("year", "make", "model"):
        assert re.search(rf'<input id="{name}" name="{name}" type="text"', html)
    assert '<select id="category" name="category"' in html
    options = re.findall(r'<option value="([^"]*)"', re.search(r'<select id="category".*?</select>', html, re.S).group(0))
    assert options == ["road", "gravel", "mountain", "hybrid", "e-bike", "other"]
    assert html.count("<select") == 1  # no make/model lists
    assert "optgroup" not in html and "catalog_id" not in html
    assert 'name="manual_baseline_mileage"' in html


def test_creating_a_bike_derives_its_name_and_uses_the_category(signed_in_client):
    response = signed_in_client.post(
        "/bikes", data={**DOMANE, "category": "gravel", "manual_baseline_mileage": "12.5"}, follow_redirects=False
    )

    assert response.status_code == 303 and response.headers["location"] == "/bikes/1"
    bike = bike_service.get_bike(1)
    assert (bike.name, bike.bike_type, bike.year, bike.make, bike.model) == ("2022 Trek Domane", "gravel", 2022, "Trek", "Domane")
    assert bike.total_mileage == 12.5


def test_the_same_bike_twice_gets_a_suffix(signed_in_client):
    for _ in range(2):
        signed_in_client.post("/bikes", data=DOMANE)

    assert [b.name for b in bike_service.list_bikes()] == ["2022 Trek Domane", "2022 Trek Domane (2)"]


@pytest.mark.parametrize(
    "change,field",
    [
        ({"year": ""}, "year"),
        ({"year": "abc"}, "year"),
        ({"year": "1850"}, "year"),
        ({"make": "  "}, None),
        ({"model": ""}, None),
        ({"category": "spaceship"}, "category"),
        ({"category": ""}, "category"),
        ({"make": "x" * 61}, "make"),
        ({"manual_baseline_mileage": "-5"}, "manual_baseline_mileage"),
    ],
)
def test_invalid_entries_are_rejected_keeping_the_other_values(signed_in_client, change, field):
    response = signed_in_client.post("/bikes", data={**DOMANE, **change})

    assert response.status_code == 422
    assert bike_service.list_bikes() == []
    assert 'class="error-summary"' in response.text
    if field:
        assert f'id="{field}-error"' in response.text
    if "model" not in change:
        assert 'value="Domane"' in response.text  # untouched entries survive


def test_edit_form_prefills_the_details(signed_in_client):
    bike_service.create_bike_from_details(year=2020, make="Giant", model="TCR", category="gravel")

    html = signed_in_client.get("/bikes/1/edit").text

    assert 'value="2020"' in html and 'value="Giant"' in html and 'value="TCR"' in html
    assert re.search(r'<option value="gravel" selected>', html)
    assert "single name" not in html


def test_edit_form_for_a_legacy_bike_explains_the_single_name(signed_in_client):
    bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    html = signed_in_client.get("/bikes/1/edit").text

    assert "single name" in html and "Grandpa&#39;s Raleigh" in html
    assert re.search(r'<option value="other" selected>', html)  # unknown legacy type maps to other
    assert not re.search(r'<input id="year"[^>]*required', html)


def test_editing_a_legacy_bike_with_blank_details_keeps_the_name(signed_in_client):
    bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    response = signed_in_client.post(
        "/bikes/1", data={"year": "", "make": "", "model": "", "category": "road", "manual_baseline_mileage": "9"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    bike = bike_service.get_bike(1)
    assert (bike.name, bike.bike_type, bike.manual_baseline_mileage) == ("Grandpa's Raleigh", "road", 9)


def test_editing_with_a_mix_of_blank_and_filled_details_is_refused(signed_in_client):
    bike_service.create_bike(name="Grandpa's Raleigh")

    response = signed_in_client.post("/bikes/1", data={"year": "1975", "make": "", "model": "", "category": "road"})

    assert response.status_code == 422
    assert bike_service.get_bike(1).name == "Grandpa's Raleigh"


def test_editing_renames_the_bike(signed_in_client):
    bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="road")

    signed_in_client.post("/bikes/1", data={"year": "2023", "make": "Canyon", "model": "Grizl", "category": "gravel"})

    assert bike_service.get_bike(1).name == "2023 Canyon Grizl"


def test_editing_a_missing_bike_is_a_404(signed_in_client):
    assert signed_in_client.post("/bikes/99", data=DOMANE).status_code == 404


def test_the_add_and_edit_pages_show_a_breadcrumb(signed_in_client):
    bike_service.create_bike_from_details(year=2022, make="Trek", model="Domane", category="road")

    add = signed_in_client.get("/bikes/new").text
    edit = signed_in_client.get("/bikes/1/edit").text

    assert '<nav class="breadcrumb" aria-label="Breadcrumb">' in add and '<a href="/">Garage</a>' in add
    assert '<a href="/bikes/1">2022 Trek Domane</a>' in edit and 'aria-current="page"><span>Edit</span>' in edit
