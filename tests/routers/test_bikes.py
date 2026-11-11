import pytest


@pytest.mark.parametrize(
    "method,path,data",
    [
        ("get", "/", None),
        ("get", "/bikes/1", None),
        ("get", "/bikes/new", None),
        ("post", "/bikes", {"catalog_id": "trek-domane", "manual_baseline_mileage": "0"}),
        ("get", "/bikes/1/edit", None),
        ("post", "/bikes/1", {"catalog_id": "trek-domane", "manual_baseline_mileage": "0"}),
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

    client.post("/bikes", data={"catalog_id": "canyon-grizl", "manual_baseline_mileage": "0"})
    response = client.get("/")

    assert response.status_code == 200
    assert "Canyon Grizl" in response.text


def test_create_then_view_bike_detail(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"catalog_id": "trek-domane", "manual_baseline_mileage": "10"})

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Trek Domane'").fetchone()["id"]

    response = client.get(f"/bikes/{bike_id}")

    assert response.status_code == 200
    assert "Trek Domane" in response.text


def test_delete_bike_with_installed_component_returns_confirmation_fragment(client, monkeypatch):
    _login(client, monkeypatch)

    client.post("/bikes", data={"catalog_id": "trek-fx", "manual_baseline_mileage": "0"})

    from app.db import connection

    with connection.get_connection() as conn:
        bike_id = conn.execute("SELECT id FROM bike WHERE name = 'Trek FX'").fetchone()["id"]

    client.post(
        "/components",
        data={"name": "Wheel", "component_type": "wheel", "parent_bike_id": str(bike_id)},
    )

    response = client.post(f"/bikes/{bike_id}/delete", data={})

    assert response.status_code == 200
    assert "onfirm" in response.text

    response = client.post(f"/bikes/{bike_id}/delete", data={"confirmed": "true"})
    assert response.status_code in (200, 303)

    with connection.get_connection() as conn:
        row = conn.execute("SELECT is_deleted FROM bike WHERE id = ?", (bike_id,)).fetchone()
    assert row["is_deleted"] == 1


# ------------------------------------------------ catalog form (specs/004-bike-builder, M1)

import re  # noqa: E402

from app.services import bike_service  # noqa: E402


def test_add_form_is_a_catalog_select_with_no_free_text(signed_in_client):
    html = signed_in_client.get("/bikes/new").text

    assert '<select id="catalog_id" name="catalog_id"' in html
    assert 'name="name"' not in html and 'name="bike_type"' not in html
    for label in ("Road", "Gravel", "Mountain", "Hybrid", "E-bike"):
        assert f'<optgroup label="{label}">' in html
    assert '<option value="trek-domane">Trek Domane</option>' in html
    assert 'name="manual_baseline_mileage"' in html


def test_creating_from_the_catalog_names_and_types_the_bike(signed_in_client):
    response = signed_in_client.post(
        "/bikes", data={"catalog_id": "specialized-diverge", "manual_baseline_mileage": "12.5"},
        follow_redirects=False,
    )

    assert response.status_code == 303 and response.headers["location"] == "/bikes/1"
    bike = bike_service.get_bike(1)
    assert (bike.name, bike.bike_type, bike.catalog_id) == ("Specialized Diverge", "gravel", "specialized-diverge")
    assert bike.total_mileage == 12.5


def test_adding_the_same_model_twice_suffixes_the_second(signed_in_client):
    for _ in range(2):
        signed_in_client.post("/bikes", data={"catalog_id": "trek-domane"})

    assert [b.name for b in bike_service.list_bikes()] == ["Trek Domane", "Trek Domane (2)"]


@pytest.mark.parametrize("value", ["", "nope", "Trek Domane", "__keep__", "<script>"])
def test_unknown_or_missing_catalog_ids_are_rejected_with_a_field_error(signed_in_client, value):
    response = signed_in_client.post("/bikes", data={"catalog_id": value})

    assert response.status_code == 422
    assert 'class="field-error"' in response.text
    assert bike_service.list_bikes() == []


def test_free_text_name_and_type_are_ignored(signed_in_client):
    signed_in_client.post(
        "/bikes", data={"catalog_id": "trek-domane", "name": "Hacked", "bike_type": "bmx"}
    )

    bike = bike_service.get_bike(1)
    assert (bike.name, bike.bike_type) == ("Trek Domane", "road")


def test_negative_baseline_mileage_is_rejected_and_the_choice_kept(signed_in_client):
    response = signed_in_client.post(
        "/bikes", data={"catalog_id": "trek-domane", "manual_baseline_mileage": "-5"}
    )

    assert response.status_code == 422
    assert re.search(r'<option value="trek-domane" selected>', response.text)


def test_edit_form_preselects_the_current_catalog_entry(signed_in_client):
    bike_service.create_bike_from_catalog("giant-tcr")

    html = signed_in_client.get("/bikes/1/edit").text

    assert re.search(r'<option value="giant-tcr" selected>', html)
    assert "__keep__" not in html


def test_edit_form_for_a_legacy_bike_offers_keep_current(signed_in_client):
    bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    html = signed_in_client.get("/bikes/1/edit").text

    assert re.search(r'<option value="__keep__" selected>Keep current: Grandpa&#39;s Raleigh', html)


def test_editing_a_legacy_bike_with_keep_current_changes_only_the_mileage(signed_in_client):
    bike_service.create_bike(name="Grandpa's Raleigh", bike_type="vintage")

    response = signed_in_client.post(
        "/bikes/1", data={"catalog_id": "__keep__", "manual_baseline_mileage": "9"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    bike = bike_service.get_bike(1)
    assert (bike.name, bike.bike_type, bike.manual_baseline_mileage) == ("Grandpa's Raleigh", "vintage", 9)


def test_editing_to_another_catalog_entry_renames_the_bike(signed_in_client):
    bike_service.create_bike_from_catalog("trek-domane")

    signed_in_client.post("/bikes/1", data={"catalog_id": "canyon-grizl", "manual_baseline_mileage": "0"})

    assert bike_service.get_bike(1).name == "Canyon Grizl"


def test_editing_a_missing_bike_is_a_404(signed_in_client):
    assert signed_in_client.post("/bikes/99", data={"catalog_id": "trek-domane"}).status_code == 404
