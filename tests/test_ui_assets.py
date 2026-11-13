"""Pages request their css and scripts by versioned addresses (specs/020, FR-014)."""

import re
from pathlib import Path

from app.services import bike_service

TEMPLATES = Path("app/templates")


def _versioned(html, name):
    return re.search(rf'(?:href|src)="[^"]*/static/{re.escape(name)}\?v=[0-9a-f]{{8,}}"', html) is not None


def test_the_sign_in_page_links_versioned_css_and_scripts(client):
    html = client.get("/login").text

    for name in ("styles.css", "htmx.min.js", "localtime.js"):
        assert _versioned(html, name), name


def test_the_bike_screen_links_a_versioned_builder_script(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert _versioned(html, "builder.js") and _versioned(html, "styles.css")


def test_no_template_requests_css_or_js_without_a_version():
    offenders = []
    for path in TEMPLATES.rglob("*.html"):
        for line in path.read_text().splitlines():
            if re.search(r"url_for\('static', path='[^']*\.(css|js)'\)", line):
                offenders.append(f"{path}: {line.strip()[:80]}")
    assert offenders == []


def test_a_versioned_address_serves_the_file(client):
    html = client.get("/login").text
    href = re.search(r'href="([^"]*/static/styles\.css\?v=[0-9a-f]+)"', html).group(1)

    response = client.get(href[href.index("/static/"):])

    assert response.status_code == 200 and "text/css" in response.headers["content-type"]
