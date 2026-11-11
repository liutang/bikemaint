"""Theme setting in Settings (specs/003-cockpit-theme, User Story 4)."""

import re

import pytest

PAGES = ["/", "/maintenance/due", "/settings", "/bikes/new"]


def _html_tag(html: str) -> str:
    return re.search(r"<html[^>]*>", html).group(0)


def _set_theme(client, value):
    return client.post("/settings/theme", data={"theme": value}, follow_redirects=False)


def test_settings_offers_system_light_and_dark_with_system_selected_by_default(signed_in_client):
    html = signed_in_client.get("/settings").text

    assert re.search(r'<h2 id="appearance-heading">Appearance</h2>', html)
    assert 'action="/settings/theme"' in html
    for value in ("system", "light", "dark"):
        assert re.search(rf'<input type="radio" id="theme-{value}" name="theme" value="{value}"', html)
    assert re.search(r'value="system"[^>]*checked', html)
    assert not re.search(r'value="(light|dark)"[^>]*checked', html)


@pytest.mark.parametrize("value", ["light", "dark"])
def test_saving_a_theme_sets_a_cookie_and_redirects_to_settings(signed_in_client, value):
    response = _set_theme(signed_in_client, value)

    assert response.status_code == 303
    assert response.headers["location"] == "/settings"
    cookie = response.headers["set-cookie"]
    assert f"theme={value}" in cookie
    assert "Max-Age=31536000" in cookie and "SameSite=lax" in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie


@pytest.mark.parametrize("value", ["light", "dark"])
def test_chosen_theme_is_applied_to_every_page_before_paint(signed_in_client, value):
    _set_theme(signed_in_client, value)

    for path in PAGES:
        assert f'data-theme="{value}"' in _html_tag(signed_in_client.get(path).text), path
    assert f'data-theme="{value}"' in _html_tag(signed_in_client.get("/login").text)


def test_settings_page_preselects_the_saved_theme(signed_in_client):
    _set_theme(signed_in_client, "dark")

    html = signed_in_client.get("/settings").text

    assert re.search(r'value="dark"[^>]*checked', html)
    assert not re.search(r'value="system"[^>]*checked', html)


def test_system_follows_the_device_again(signed_in_client):
    _set_theme(signed_in_client, "dark")

    response = _set_theme(signed_in_client, "system")

    assert response.status_code == 303
    signed_in_client.cookies.set("theme", "system")
    assert "data-theme" not in _html_tag(signed_in_client.get("/").text)
    assert "theme=" in response.headers["set-cookie"]  # cookie is cleared or set to system


def test_default_has_no_forced_theme(signed_in_client):
    assert "data-theme" not in _html_tag(signed_in_client.get("/").text)


@pytest.mark.parametrize("value", ["", "blue", "DARK", "<script>"])
def test_invalid_theme_is_rejected_and_the_saved_choice_is_unchanged(signed_in_client, value):
    _set_theme(signed_in_client, "dark")

    response = _set_theme(signed_in_client, value)

    assert response.status_code == 422
    assert "set-cookie" not in response.headers
    assert 'data-theme="dark"' in _html_tag(signed_in_client.get("/").text)


def test_a_tampered_cookie_value_is_ignored(signed_in_client):
    signed_in_client.cookies.set("theme", '"><script>alert(1)</script>')

    html = signed_in_client.get("/").text

    assert "data-theme" not in _html_tag(html)
    assert "<script>alert(1)" not in html


def test_saving_the_theme_requires_sign_in(client):
    response = client.post("/settings/theme", data={"theme": "dark"}, follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/login")
