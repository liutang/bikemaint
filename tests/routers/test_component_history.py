"""Install dates on add and the manual parts-history screens (specs/015)."""

import pytest

from app.db import connection, mileage as mileage_db
from app.services import bike_service, component_history_service as history, component_service


def _ride(bike, activity_id, miles, when):
    with connection.get_connection() as conn:
        mileage_db.upsert_ride_activity(
            conn, strava_activity_id=activity_id, strava_gear_id="g", bike_id=bike.id,
            distance_miles=miles, occurred_at=when,
        )


def _miles(component_id):
    return component_service.get_component(component_id).total_mileage


@pytest.mark.parametrize(
    "method,path",
    [("get", "/components/1/install-history"), ("get", "/components/1/install-history/new"),
     ("post", "/components/1/install-history"), ("get", "/install-periods/1/edit"),
     ("post", "/install-periods/1"), ("post", "/install-periods/1/delete")],
)
def test_routes_require_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_missing_part_or_period_is_a_404(signed_in_client):
    assert signed_in_client.get("/components/99/install-history").status_code == 404
    assert signed_in_client.get("/components/99/install-history/new").status_code == 404
    assert signed_in_client.post("/components/99/install-history", data={}).status_code == 404
    assert signed_in_client.get("/install-periods/99/edit").status_code == 404
    assert signed_in_client.post("/install-periods/99", data={}).status_code == 404
    assert signed_in_client.post("/install-periods/99/delete").status_code == 404


def _form(bike, **kw):
    return {
        "bike_id": str(bike.id), "installed_date": "2025-01-01", "installed_time": "",
        "removed_date": "2025-07-01", "removed_time": "", **kw,
    }


def test_logging_a_period_recomputes_mileage_and_lists_it(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    saddle = component_service.create_component(name="Saddle", component_type="saddle")
    _ride(bike, 1, 25, "2025-03-01T08:00:00.000000Z")
    response = signed_in_client.post(
        f"/components/{saddle.id}/install-history", data=_form(bike), follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/components/{saddle.id}/install-history"
    assert _miles(saddle.id) == 25
    page = signed_in_client.get(f"/components/{saddle.id}/install-history").text
    assert "Road A" in page and "2025-01-01" in page and "2025-07-01" in page and "25.0" in page


def test_overlap_and_bad_input_rerender_with_errors(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    saddle = component_service.create_component(name="Saddle", component_type="saddle")
    path = f"/components/{saddle.id}/install-history"
    assert signed_in_client.post(path, data=_form(bike), follow_redirects=False).status_code == 303
    clash = signed_in_client.post(path, data=_form(bike, installed_date="2025-03-01", removed_date="2025-09-01"))
    assert clash.status_code == 422 and "overlaps" in clash.text
    assert len(history.list_history(saddle.id)) == 1
    backwards = signed_in_client.post(path, data=_form(bike, installed_date="2025-09-01", removed_date="2025-08-01"))
    assert backwards.status_code == 422 and "after the install" in backwards.text
    blank = signed_in_client.post(path, data=_form(bike, installed_date=""))
    assert blank.status_code == 422
    nobike = signed_in_client.post(path, data=_form(bike, bike_id="99"))
    assert nobike.status_code == 422


def test_edit_and_delete_a_period(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    saddle = component_service.create_component(name="Saddle", component_type="saddle")
    _ride(bike, 1, 25, "2025-03-01T08:00:00.000000Z")
    period = history.log_period(
        saddle.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z", removed_at="2025-07-01T00:00:00.000000Z",
    )
    assert "2025-01-01" in signed_in_client.get(f"/install-periods/{period.id}/edit").text
    response = signed_in_client.post(
        f"/install-periods/{period.id}", data=_form(bike, installed_date="2025-04-01"), follow_redirects=False
    )
    assert response.status_code == 303
    assert _miles(saddle.id) == 0
    bad = signed_in_client.post(f"/install-periods/{period.id}", data=_form(bike, removed_date="2025-01-01"))
    assert bad.status_code == 422
    response = signed_in_client.post(f"/install-periods/{period.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert history.list_history(saddle.id) == []


def test_the_live_period_cannot_be_deleted(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)
    live = history.list_history(saddle.id)[0]
    response = signed_in_client.post(f"/install-periods/{live.id}/delete", follow_redirects=False)
    assert response.status_code == 422
    assert len(history.list_history(saddle.id)) == 1


def test_the_part_screen_links_to_install_history(signed_in_client):
    saddle = component_service.create_component(name="Saddle", component_type="saddle")
    html = signed_in_client.get(f"/components/{saddle.id}").text
    assert f'href="/components/{saddle.id}/install-history"' in html


# ---------------------------------------------------------------- builder add with a date


def test_adding_from_the_palette_with_an_install_date_counts_rides_since(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    _ride(bike, 1, 10, "2025-01-15T08:00:00.000000Z")
    _ride(bike, 2, 5, "2025-03-15T08:00:00.000000Z")
    response = signed_in_client.post(
        "/builder/add",
        data={"root": f"bike:{bike.id}", "component_type": "saddle", "target": f"bike:{bike.id}",
              "installed_date": "2025-03-01", "installed_time": "09:00"},
        headers={"hx-request": "true"},
    )
    assert response.status_code == 200
    saddle = next(c for c in component_service.get_tree_for_bike(bike.id) if c.component_type == "saddle")
    assert saddle.total_mileage == 5
    assert history.list_history(saddle.id)[0].installed_at == "2025-03-01T09:00:00.000000Z"


def test_adding_with_a_future_or_malformed_date_is_refused(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    base = {"root": f"bike:{bike.id}", "component_type": "saddle", "target": f"bike:{bike.id}"}
    for extra in ({"installed_date": "2999-01-01"}, {"installed_date": "nope"}, {"installed_time": "09:00"}):
        response = signed_in_client.post("/builder/add", data={**base, **extra}, headers={"hx-request": "true"})
        assert response.status_code == 422
    assert component_service.get_tree_for_bike(bike.id) == []


def test_the_add_form_offers_date_and_time(signed_in_client):
    bike = bike_service.create_bike(name="Road A")
    html = signed_in_client.get(f"/bikes/{bike.id}").text
    assert 'name="installed_date"' in html and 'name="installed_time"' in html


# ------------------------------------------------ specs/022: a bike's install history screen


def test_bike_install_history_requires_sign_in(client):
    response = client.get("/bikes/1/install-history", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_an_unknown_bike_is_a_404(signed_in_client):
    assert signed_in_client.get("/bikes/99/install-history").status_code == 404


def test_the_bike_screen_links_to_its_install_history_beside_maintenance_history(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert f'href="/bikes/{bike.id}/install-history">Install history</a>' in html
    assert html.index(">Maintenance history<") < html.index(">Install history<")


def test_the_empty_bike_history_says_so(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history").text

    assert "No parts have been installed yet" in html and "<form" not in html.split("</header>")[-1]


def test_the_bike_history_lists_parts_newest_first_read_only(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain", parent_bike_id=bike.id)
    component_service.move_component(chain.id)  # to storage: closes its period
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history").text

    assert html.index("Tire") < html.index("Wheel") < html.index("Old chain")  # newest installed first
    assert "Still installed" in html and html.count("Still installed") == 2
    assert f'href="/components/{tire.id}"' in html and f'href="/components/{chain.id}"' in html
    assert "Front" not in html and 'class="chip">Chain</span>' in html
    body = html.split("<tbody>")[1]
    assert "<form" not in body and "Edit" not in body and "Delete" not in body
