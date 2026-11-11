"""App shell checks (specs/002-modern-ui, User Story 1)."""

import re

import pytest

PAGES = ["/", "/components", "/maintenance/due", "/settings", "/bikes/new"]


def _count(pattern: str, html: str) -> int:
    return len(re.findall(pattern, html))


@pytest.mark.parametrize("path", PAGES)
def test_every_page_has_the_shell_landmarks(signed_in_client, path):
    html = signed_in_client.get(path).text

    assert 'class="skip-link" href="#main"' in html
    assert _count(r"<header\b", html) == 1
    assert '<nav aria-label="Primary">' in html
    for href in ("/", "/maintenance/due", "/settings"):
        assert f'<a href="{href}"' in html
    assert '<form method="post" action="/logout">' in html
    assert '<main id="main"' in html
    assert _count(r"<h1\b", html) == 1
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    assert re.search(r"<title>[^<]+</title>", html)


def _current_links(html: str) -> list[str]:
    return re.findall(r'<a href="([^"]+)"[^>]*aria-current="page"', html)


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/", "/"),
        ("/bikes/new", "/"),
        ("/components", "/"),
        ("/maintenance/due", "/maintenance/due"),
        ("/settings", "/settings"),
    ],
)
def test_current_section_is_marked_exactly_once(signed_in_client, path, expected):
    assert _current_links(signed_in_client.get(path).text) == [expected]


def test_login_page_has_the_brand_but_no_navigation(client):
    html = client.get("/login").text

    assert _count(r"<header\b", html) == 1
    assert 'class="brand"' in html
    assert _count(r"<h1\b", html) == 1
    assert "Sign in with Strava" in html
    for forbidden in ('href="/maintenance/due"', 'href="/settings"', 'action="/logout"'):
        assert forbidden not in html


def test_theme_color_scheme_meta_is_declared(client):
    assert '<meta name="color-scheme" content="light dark">' in client.get("/login").text
