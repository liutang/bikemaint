"""Storage is reachable and the garage lists bikes only (specs/006-feedback-round-2, M1)."""

import re

from app.services import bike_service, component_service


def _bike(name="Road"):
    return bike_service.create_bike(name=name)


def test_the_garage_lists_only_bikes_and_links_to_storage(signed_in_client):
    _bike("Gravel")
    component_service.create_component(name="Spare saddle", component_type="saddle")
    component_service.create_component(name="Spare wheel", component_type="wheel")

    html = signed_in_client.get("/").text

    assert "Gravel" in html
    assert "Spare saddle" not in html and "Spare wheel" not in html
    assert not re.search(r"<h2[^>]*>\s*In storage", html)
    link = re.search(r'<a class="btn" href="/components">(.*?)</a>', html, re.S)
    assert link and "Storage" in link.group(1) and "2" in link.group(1)  # how many parts are stored


def test_the_storage_link_shows_zero_when_empty(signed_in_client):
    html = signed_in_client.get("/").text

    link = re.search(r'<a class="btn" href="/components">(.*?)</a>', html, re.S)
    assert link and "Storage" in link.group(1)


def test_an_empty_garage_only_talks_about_bikes(signed_in_client):
    html = signed_in_client.get("/").text

    assert html.count('class="empty-state"') == 1 and "No bikes yet" in html
    assert "Nothing in storage" not in html


def test_the_navigation_has_a_storage_link_with_the_current_page_marked(signed_in_client):
    for path, expected in (("/components", "/components"), ("/components/new", "/components"), ("/", "/")):
        html = signed_in_client.get(path).text
        assert 'href="/components"' in re.search(r'<nav aria-label="Primary">.*?</nav>', html, re.S).group(0)
        current = re.findall(r'<a href="([^"]+)"[^>]*aria-current="page"', html)
        assert current == [expected], (path, current)


def test_a_part_screen_does_not_mark_storage_as_current(signed_in_client):
    bike = _bike()
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    assert re.findall(r'<a href="([^"]+)"[^>]*aria-current="page"', html) == ["/"]


def test_the_storage_screen_has_breadcrumbs_cards_and_an_add_button(signed_in_client):
    component_service.create_component(name="Spare saddle", component_type="saddle")

    html = signed_in_client.get("/components").text

    crumbs = re.search(r'<nav class="breadcrumb" aria-label="Breadcrumb">.*?</nav>', html, re.S).group(0)
    assert '<a href="/">Garage</a>' in crumbs and 'aria-current="page"><span>Storage</span>' in crumbs
    assert re.search(r"<h1[^>]*>\s*Storage\s*</h1>", html)
    assert "Spare saddle" in html and 'href="/components/new"' in html
    assert "In Storage" not in html


def test_the_empty_storage_screen_explains_itself(signed_in_client):
    html = signed_in_client.get("/components").text

    assert "Nothing in storage" in html and 'href="/components/new"' in html


def test_the_add_part_and_edit_part_pages_have_breadcrumbs(signed_in_client):
    bike = _bike("Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    spare = component_service.create_component(name="Spare", component_type="saddle")

    add = signed_in_client.get("/components/new").text
    edit_mounted = signed_in_client.get(f"/components/{wheel.id}/edit").text
    edit_stored = signed_in_client.get(f"/components/{spare.id}/edit").text

    assert 'href="/components">Storage</a>' in add and 'aria-current="page"><span>Add a part</span>' in add
    assert f'href="/bikes/{bike.id}">Road</a>' in edit_mounted and 'aria-current="page"><span>Edit</span>' in edit_mounted
    assert f'href="/components/{wheel.id}">Wheel</a>' in edit_mounted
    assert 'href="/components">Storage</a>' in edit_stored
