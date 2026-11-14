"""Install dates on add and the manual parts-history screens (specs/015)."""

import re

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


def test_the_bike_history_lists_parts_newest_first_with_edit_controls(signed_in_client):
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
    assert body.count(">Edit</a>") == 3 and body.count(">Delete</button>") == 1  # only the removed chain
    assert f"?from_bike={bike.id}" in body
    assert f'href="/bikes/{bike.id}/install-history/new"' in html and "Log a period" in html




# ------------------------------------------------ specs/022 US4: editing from the bike


def _periods(component):
    return history.list_history(component.id)


def _period_form(**kw):
    return {"installed_date": "2025-04-01", "installed_time": "", "removed_date": "2025-06-01",
            "removed_time": "", "parent_component_id": "", **kw}


@pytest.mark.parametrize(
    "method,path",
    [("get", "/bikes/1/install-history/new"), ("post", "/bikes/1/install-history")],
)
def test_the_new_bike_routes_require_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_unknown_bike_is_a_404_for_the_new_routes(signed_in_client):
    assert signed_in_client.get("/bikes/99/install-history/new").status_code == 404
    assert signed_in_client.post("/bikes/99/install-history", data={}).status_code == 404


def test_the_empty_bike_history_still_offers_log_a_period(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history").text

    assert f'href="/bikes/{bike.id}/install-history/new"' in html


def test_the_bike_form_names_the_bike_and_offers_active_parts_to_choose(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)
    gone = component_service.create_component(name="Gone", component_type="saddle")
    component_service.delete_component(gone.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history/new").text

    assert "Road" in html and 'name="component_id"' in html
    assert f'<option value="{saddle.id}"' in html and "Gone" not in html
    assert 'name="installed_date"' in html and 'name="removed_date"' in html
    assert f'href="/bikes/{bike.id}/install-history">Cancel</a>' in html


def test_logging_a_past_period_from_the_bike_records_it_and_returns_to_the_bike_history(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    _ride(bike, 1, 40, "2025-05-01T08:00:00.000000Z")

    response = signed_in_client.post(
        f"/bikes/{bike.id}/install-history", data=_period_form(component_id=str(chain.id)), follow_redirects=False
    )

    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}/install-history")
    (period,) = _periods(chain)
    assert (period.parent_bike_id, period.installed_at[:10], period.removed_at[:10]) == (bike.id, "2025-04-01", "2025-06-01")
    assert component_service.get_component(chain.id).total_mileage == 40  # the part's mileage was recalculated
    assert "Old chain" in signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    assert "2025-04-01" in signed_in_client.get(f"/components/{chain.id}/install-history").text  # same period


def test_a_past_period_can_say_which_part_it_was_inside(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire")

    signed_in_client.post(
        f"/bikes/{bike.id}/install-history",
        data=_period_form(component_id=str(tire.id), parent_component_id=str(wheel.id)),
    )

    assert _periods(tire)[0].parent_component_id == wheel.id


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"removed_date": "2025-03-01"}, "after"),
        ({"installed_date": "2999-01-01", "removed_date": "2999-02-01"}, "future"),
        ({"component_id": "999"}, "part"),
        ({"component_id": ""}, "part"),
    ],
)
def test_invalid_entries_show_the_form_again_with_a_message_and_record_nothing(signed_in_client, changes, message):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    data = _period_form(component_id=str(chain.id))
    data.update(changes)

    response = signed_in_client.post(f"/bikes/{bike.id}/install-history", data=data)

    assert response.status_code == 422 and message in response.text.lower()
    assert _periods(chain) == []


def test_overlapping_another_period_of_the_same_part_is_refused(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    history.log_period(chain.id, bike_id=bike.id, installed_at="2025-03-01T00:00:00.000000Z",
                       removed_at="2025-05-01T00:00:00.000000Z")

    response = signed_in_client.post(f"/bikes/{bike.id}/install-history", data=_period_form(component_id=str(chain.id)))

    assert response.status_code == 422 and "overlap" in response.text.lower()
    assert len(_periods(chain)) == 1


def test_edit_from_the_bike_returns_to_the_bike_history(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    period = history.log_period(chain.id, bike_id=bike.id, installed_at="2025-04-01T00:00:00.000000Z",
                                removed_at="2025-06-01T00:00:00.000000Z")
    back = f"/bikes/{bike.id}/install-history"

    page = signed_in_client.get(f"/install-periods/{period.id}/edit?from_bike={bike.id}").text
    assert f'action="/install-periods/{period.id}?from_bike={bike.id}"' in page
    assert f'href="{back}">Cancel</a>' in page

    response = signed_in_client.post(
        f"/install-periods/{period.id}?from_bike={bike.id}",
        data={"bike_id": str(bike.id), **_period_form(removed_date="2025-07-01")}, follow_redirects=False,
    )
    assert (response.status_code, response.headers["location"]) == (303, back)
    assert _periods(chain)[0].removed_at[:10] == "2025-07-01"


def test_edit_without_from_bike_still_returns_to_the_part(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    period = history.log_period(chain.id, bike_id=bike.id, installed_at="2025-04-01T00:00:00.000000Z",
                                removed_at="2025-06-01T00:00:00.000000Z")

    response = signed_in_client.post(
        f"/install-periods/{period.id}", data={"bike_id": str(bike.id), **_period_form()}, follow_redirects=False
    )

    assert response.headers["location"] == f"/components/{chain.id}/install-history"


@pytest.mark.parametrize("bad", ["abc", "-1", "0", "999", ""])
def test_a_bad_from_bike_is_ignored(signed_in_client, bad):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    period = history.log_period(chain.id, bike_id=bike.id, installed_at="2025-04-01T00:00:00.000000Z",
                                removed_at="2025-06-01T00:00:00.000000Z")

    response = signed_in_client.post(
        f"/install-periods/{period.id}/delete?from_bike={bad}", follow_redirects=False
    )

    assert response.headers["location"] == f"/components/{chain.id}/install-history"


def test_delete_from_the_bike_returns_to_the_bike_history_and_removes_the_period(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Old chain", component_type="chain")
    period = history.log_period(chain.id, bike_id=bike.id, installed_at="2025-04-01T00:00:00.000000Z",
                                removed_at="2025-06-01T00:00:00.000000Z")

    response = signed_in_client.post(
        f"/install-periods/{period.id}/delete?from_bike={bike.id}", follow_redirects=False
    )

    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}/install-history")
    assert _periods(chain) == []


def test_a_live_period_cannot_be_deleted_from_the_bike(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)
    (period,) = _periods(saddle)

    response = signed_in_client.post(f"/install-periods/{period.id}/delete?from_bike={bike.id}")

    assert response.status_code == 422 and len(_periods(saddle)) == 1


def test_rows_of_deleted_parts_have_no_edit_and_say_deleted(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    saddle = component_service.create_component(name="Saddle", component_type="saddle", parent_bike_id=bike.id)
    component_service.delete_component(saddle.id, keep_history=True)

    body = signed_in_client.get(f"/bikes/{bike.id}/install-history").text.split("<tbody>")[1]

    assert "Saddle (deleted)" in _text(body) and ">Edit</a>" not in body


# ------------------------------------------------ specs/030: ending by edit, deleted rows, button border


def _text(html):
    """The visible text of some markup: tags dropped, spaces collapsed."""
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _live(bike, name="Chain", kind="chain", when="2025-01-01T00:00:00.000000Z"):
    part = component_service.create_component(name=name, component_type=kind, parent_bike_id=bike.id, installed_at=when)
    return part, history.list_history(part.id)[-1]


def test_the_edit_form_of_an_open_period_offers_blank_removed_fields(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain, period = _live(bike)

    html = signed_in_client.get(f"/install-periods/{period.id}/edit").text

    assert re.search(r'<input id="removed_date"[^>]*value=""', html)
    assert re.search(r'<input id="removed_time"[^>]*value=""', html)
    assert "ends the installation" in html and "storage" in html
    assert not re.search(r'<input id="removed_date"[^>]*required', html)  # optional for an open period


def test_saving_a_valid_removed_moment_moves_the_part_to_storage(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain, period = _live(bike)
    _ride(bike, 1, 10, "2025-02-01T08:00:00.000000Z")
    _ride(bike, 2, 20, "2025-06-01T08:00:00.000000Z")

    response = signed_in_client.post(
        f"/install-periods/{period.id}",
        data={"bike_id": str(bike.id), "installed_date": "2025-01-01", "installed_time": "",
              "removed_date": "2025-03-01", "removed_time": "", "parent_component_id": ""},
        follow_redirects=False,
    )

    assert (response.status_code, response.headers["location"]) == (303, f"/components/{chain.id}/install-history")
    assert component_service.get_component(chain.id).parent_bike_id is None
    assert _miles(chain.id) == 10


def test_ending_from_the_bike_history_returns_to_the_bike(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain, period = _live(bike)

    response = signed_in_client.post(
        f"/install-periods/{period.id}?from_bike={bike.id}",
        data={"bike_id": str(bike.id), "installed_date": "2025-01-01", "removed_date": "2025-03-01"},
        follow_redirects=False,
    )

    assert response.headers["location"] == f"/bikes/{bike.id}/install-history"
    assert component_service.get_component(chain.id).parent_bike_id is None


@pytest.mark.parametrize("removed,message", [("2025-01-01", "after"), ("2024-12-31", "after"), ("2999-01-01", "future")])
def test_a_removed_moment_that_is_not_possible_shows_a_message_and_changes_nothing(signed_in_client, removed, message):
    bike = bike_service.create_bike(name="Road")
    chain, period = _live(bike)

    response = signed_in_client.post(
        f"/install-periods/{period.id}",
        data={"bike_id": str(bike.id), "installed_date": "2025-01-01", "removed_date": removed},
    )

    assert response.status_code == 422 and message in response.text.lower()
    assert 'id="removed_date-error"' in response.text
    assert component_service.get_component(chain.id).parent_bike_id == bike.id


def test_install_history_delete_buttons_are_bordered(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain")
    history.log_period(chain.id, bike_id=bike.id, installed_at="2025-01-01T00:00:00.000000Z",
                       removed_at="2025-02-01T00:00:00.000000Z")

    for url in (f"/components/{chain.id}/install-history", f"/bikes/{bike.id}/install-history"):
        html = signed_in_client.get(url).text
        button = re.search(r'<button class="([^"]*)" type="submit">Delete</button>', html).group(1).split()
        assert "btn" in button and "btn-quiet" not in button, url


def test_rows_of_deleted_parts_say_deleted_and_can_be_deleted_one_by_one(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    a = component_service.create_component(name="Hub", component_type="hub", parent_bike_id=bike.id)
    b = component_service.create_component(name="Hub", component_type="hub", parent_bike_id=bike.id)
    component_service.delete_component(a.id, keep_history=True)
    component_service.delete_component(b.id, keep_history=True)

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    body = html.split("<tbody>")[1]

    assert _text(body).count("Hub (deleted)") == 2
    assert ">Edit</a>" not in body and body.count(">Delete</button>") == 2
    (first,) = history.list_history(a.id)

    response = signed_in_client.post(f"/install-periods/{first.id}/delete?from_bike={bike.id}", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, f"/bikes/{bike.id}/install-history")
    assert history.list_history(a.id) == [] and len(history.list_history(b.id)) == 1


def test_a_live_period_of_an_existing_part_still_cannot_be_deleted_and_has_no_delete_button(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain, period = _live(bike)

    body = signed_in_client.get(f"/bikes/{bike.id}/install-history").text.split("<tbody>")[1]

    assert ">Delete</button>" not in body
    assert signed_in_client.post(f"/install-periods/{period.id}/delete").status_code == 422


# ------------------------------------------------ specs/031: place links on both screens


def test_part_history_links_existing_places_and_leaves_others_plain(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Front wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)

    html = signed_in_client.get(f"/components/{tire.id}/install-history").text

    assert f'<td data-label="Installed on"><a href="/components/{wheel.id}">Front wheel</a></td>' in html
    wheel_html = signed_in_client.get(f"/components/{wheel.id}/install-history").text
    assert f'<td data-label="Installed on"><a href="/bikes/{bike.id}">Road</a></td>' in wheel_html


def test_bike_history_links_the_place_when_it_exists(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Front wheel", component_type="wheel", parent_bike_id=bike.id)
    component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)

    body = signed_in_client.get(f"/bikes/{bike.id}/install-history").text.split("<tbody>")[1]

    assert f'<td data-label="Placed in"><a href="/components/{wheel.id}">Front wheel</a></td>' in body
    assert f'<td data-label="Placed in"><a href="/bikes/{bike.id}">Road</a></td>' in body


def test_a_deleted_parent_is_plain_text(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Front wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Tire", component_type="tire", parent_component_id=wheel.id)
    component_service.delete_component(wheel.id, confirmed=True, keep_history=True)

    body = signed_in_client.get(f"/bikes/{bike.id}/install-history").text.split("<tbody>")[1]

    assert '<td data-label="Placed in">a deleted part</td>' in body


def test_the_part_log_form_lets_the_removal_be_left_blank(signed_in_client):
    # 022 FR-012: a period for a part that is on the bike now has no removal date.
    saddle = component_service.create_component(name="Saddle", component_type="saddle")

    html = signed_in_client.get(f"/components/{saddle.id}/install-history/new").text

    removed = re.search(r'<input[^>]*name="removed_date"[^>]*>', html).group(0)
    assert "required" not in removed and "Removed on (optional)" in html


def test_the_bike_log_form_lets_the_removal_be_left_blank(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/install-history/new").text

    removed = re.search(r'<input[^>]*name="removed_date"[^>]*>', html).group(0)
    assert "required" not in removed and "Removed on (optional)" in html


def test_logging_a_period_with_no_removal_puts_the_part_on_the_bike(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain")

    response = signed_in_client.post(
        f"/components/{chain.id}/install-history",
        data=_form(bike, removed_date=""), follow_redirects=False,
    )

    assert response.status_code == 303
    assert component_service.get_component(chain.id).parent_bike_id == bike.id
    assert "Still installed" in signed_in_client.get(f"/components/{chain.id}/install-history").text


def test_a_blank_removal_from_the_bike_form_also_installs(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain")

    response = signed_in_client.post(
        f"/bikes/{bike.id}/install-history",
        data=_period_form(component_id=str(chain.id), removed_date=""), follow_redirects=False,
    )

    assert response.status_code == 303
    assert component_service.get_component(chain.id).parent_bike_id == bike.id


def test_a_part_added_now_shows_its_install_time_in_the_chosen_zone_not_utc(signed_in_client):
    # The rider's report: added at 11:05 PM local, the install time read 4:03 AM (UTC).
    from app.services import settings_service

    settings_service.set_timezone(1, "America/New_York")
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    with connection.get_connection() as conn:
        conn.execute("UPDATE component_installation_period SET installed_at = '2026-11-14T04:03:21.123456Z'")

    html = signed_in_client.get(f"/components/{chain.id}/install-history").text
    bike_html = signed_in_client.get(f"/bikes/{bike.id}/install-history").text
    form = signed_in_client.get(f"/install-periods/1/edit").text

    assert "2026-11-13 11:03PM" in html and "4:03AM" not in html
    assert "2026-11-13 11:03PM" in bike_html
    assert 'value="2026-11-13"' in form and 'value="23:03"' in form

