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


@pytest.mark.parametrize("path", PAGES)
def test_signed_in_pages_show_the_sync_indicator(signed_in_client, path):
    html = signed_in_client.get(path).text
    assert re.search(r'<span class="sync-status"[^>]*>[^<]*(Not synced yet|Synced [^<]+)</span>', html)


def test_pages_make_no_external_requests(signed_in_client, client):
    for html in (signed_in_client.get("/").text, client.get("/login").text):
        # Resource loads (stylesheets, fonts, scripts) must be local; the Strava sign-in link is navigation.
        assert not re.search(r'<link[^>]+href="https?://(?!testserver)', html)
        assert not re.search(r'<script[^>]+src="https?://(?!testserver)', html)
        assert "fonts.googleapis.com" not in html
    assert 'rel="preload"' in signed_in_client.get("/").text


def test_login_page_has_the_brand_but_no_navigation(client):
    html = client.get("/login").text

    assert _count(r"<header\b", html) == 1
    assert 'class="brand"' in html
    assert _count(r"<h1\b", html) == 1
    assert "Sign in with Strava" in html
    for forbidden in ('href="/maintenance/due"', 'href="/settings"', 'action="/logout"', "sync-status"):
        assert forbidden not in html


def test_theme_color_scheme_meta_is_declared(client):
    assert '<meta name="color-scheme" content="light dark">' in client.get("/login").text
