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
        ("/components", "/components"),
        ("/maintenance/due", "/maintenance/due"),
        ("/settings", "/settings"),
    ],
)
def test_current_section_is_marked_exactly_once(signed_in_client, path, expected):
    assert _current_links(signed_in_client.get(path).text) == [expected]


@pytest.mark.parametrize("path", PAGES)
def test_the_top_bar_shows_only_the_sync_dot_with_state_and_time_on_hover(signed_in_client, path):
    """specs/084 US2: no visible text; the hover text and accessible name carry the state and the time."""
    html = signed_in_client.get(path).text
    span = re.search(r'<span class="sync-status sync-(ok|error|off|unknown)"([^>]*)>(.*?)</span>', html, re.S)
    assert span, "the sync dot needs a state class"
    assert span.group(3).strip() == ""
    title = re.search(r'title="([^"]+)"', span.group(2)).group(1)
    assert re.search(r'aria-label="([^"]+)"', span.group(2)).group(1) == title
    assert re.match(r"(Sync is working|Sync isn&#39;t working|Automatic sync is off|Sync status unknown) · (Not synced yet|just now|\d+ (min|h|d) ago)$", title)


@pytest.mark.parametrize("path", PAGES)
def test_the_top_bar_reads_maintenance_and_sign_out_is_an_icon(signed_in_client, path):
    """specs/084 US1 and US3."""
    html = signed_in_client.get(path).text
    link = re.search(r'<a href="/maintenance/due"[^>]*>(.*?)</a>', html, re.S).group(1)
    assert re.sub(r"<[^>]+>", "", link).strip() == "Maintenance"
    button = re.search(r'<form method="post" action="/logout">\s*<button([^>]*)>(.*?)</button>', html, re.S)
    assert 'class="btn btn-icon"' in button.group(1)
    assert 'aria-label="Sign out"' in button.group(1) and 'title="Sign out"' in button.group(1)
    assert re.sub(r"<[^>]+>", "", button.group(2)).strip() == ""


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
