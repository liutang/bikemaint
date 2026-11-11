"""Rendered-page checks for the modern UI (specs/002-modern-ui, User Stories 2-4)."""

import re


def _add_bike(client, name="Road Bike", bike_type="road", baseline="12.5"):
    client.post(
        "/bikes", data={"name": name, "bike_type": bike_type, "manual_baseline_mileage": baseline}
    )


def _add_component(client, name, component_type, **parent):
    return client.post(
        "/components", data={"name": name, "component_type": component_type, **parent}
    )


# ---------------------------------------------------------------- User Story 2: garage


def test_garage_shows_bikes_as_cards_with_quick_actions(signed_in_client):
    _add_bike(signed_in_client)

    html = signed_in_client.get("/").text

    card = re.search(r'<article class="card[^"]*"[^>]*>(.*?)</article>', html, re.S)
    assert card, "bike should render as an <article class=card>"
    body = card.group(1)
    assert 'href="/bikes/1"' in body and "Road Bike" in body
    assert "road" in body
    assert "12.5 mi" in body
    assert 'href="/components/new?parent_bike_id=1"' in body and "Add component" in body
    assert 'href="/bikes/1/maintenance"' in body and "Maintenance history" in body
    assert "View" in body


def test_garage_lists_storage_under_its_own_heading(signed_in_client):
    _add_component(signed_in_client, "Spare Tire", "tire")

    html = signed_in_client.get("/").text

    assert re.search(r"<h2[^>]*>\s*In storage\s*</h2>", html)
    assert "Spare Tire" in html


def test_empty_garage_and_storage_show_guidance(signed_in_client):
    html = signed_in_client.get("/").text

    assert html.count('class="empty-state"') >= 2
    assert 'href="/bikes/new"' in html
    assert 'href="/components/new"' in html


def test_empty_storage_page_shows_an_empty_state(signed_in_client):
    html = signed_in_client.get("/components").text

    assert 'class="empty-state"' in html


def test_component_tree_uses_collapsible_details_for_branches(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")
    _add_component(signed_in_client, "Road Rim", "rim", parent_component_id="1")
    _add_component(signed_in_client, "Road Tire", "tire", parent_component_id="2")

    html = signed_in_client.get("/bikes/1").text

    assert 'class="tree"' in html
    assert html.count("<details open>") == 2  # wheel and rim have children
    assert html.count("<summary") == 2
    assert html.index("Road Wheel") < html.index("Road Rim") < html.index("Road Tire")
    start = html.rfind("<li", 0, html.index("Road Tire"))
    tire_item = html[start : html.index("</li>", start)]
    assert "<details" not in tire_item  # a leaf is a plain item, not a collapsible branch
    for kind in ("wheel", "rim", "tire"):
        assert kind in html
    assert "0.0 mi" in html or "0 mi" in html


def test_bike_without_components_shows_an_empty_state(signed_in_client):
    _add_bike(signed_in_client)

    assert 'class="empty-state"' in signed_in_client.get("/bikes/1").text


def test_unconfirmed_delete_without_htmx_returns_a_full_page_confirmation(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    response = signed_in_client.post("/bikes/1/delete", data={})

    html = response.text
    assert response.status_code == 200
    assert "<main" in html and 'aria-label="Primary"' in html
    assert 'class="confirm"' in html
    assert "btn-danger" in html
    assert 'href="/bikes/1"' in html  # cancel link


def test_unconfirmed_delete_with_htmx_returns_only_the_confirmation_fragment(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    html = signed_in_client.post(
        "/bikes/1/delete", data={}, headers={"hx-request": "true"}
    ).text

    assert 'class="confirm"' in html
    assert "<html" not in html
    assert "btn-danger" in html


def test_component_delete_confirmation_follows_the_same_contract(signed_in_client):
    _add_component(signed_in_client, "Road Wheel", "wheel")
    _add_component(signed_in_client, "Road Rim", "rim", parent_component_id="1")

    page = signed_in_client.post("/components/1/delete", data={})
    fragment = signed_in_client.post(
        "/components/1/delete", data={}, headers={"hx-request": "true"}
    )

    assert "<main" in page.text and 'class="confirm"' in page.text
    assert "<html" not in fragment.text and 'class="confirm"' in fragment.text
    assert 'href="/components/1"' in page.text


def test_confirmed_delete_still_deletes(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    signed_in_client.post("/bikes/1/delete", data={"confirmed": "true"})

    assert signed_in_client.get("/bikes/1").status_code == 404


def test_htmx_delete_without_confirmation_needed_redirects_the_whole_page(signed_in_client):
    _add_bike(signed_in_client)

    response = signed_in_client.post(
        "/bikes/1/delete", data={}, headers={"hx-request": "true"}, follow_redirects=False
    )

    assert response.status_code == 200
    assert response.headers["hx-redirect"] == "/"
    assert signed_in_client.get("/bikes/1").status_code == 404


def test_htmx_component_delete_redirects_to_storage_list(signed_in_client):
    _add_component(signed_in_client, "Spare Tire", "tire")

    response = signed_in_client.post(
        "/components/1/delete", data={}, headers={"hx-request": "true"}, follow_redirects=False
    )

    assert response.headers["hx-redirect"] == "/components"
