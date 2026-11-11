"""App icon, web manifest and theme colour (specs/009-app-icon-and-proxy)."""

import json
import re
import struct
from pathlib import Path

import pytest

STATIC = Path(__file__).parent.parent / "app" / "static"
ICONS = STATIC / "icons"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", data[16:24])


@pytest.mark.parametrize(
    "name,size",
    [("favicon-32.png", 32), ("apple-touch-icon.png", 180), ("icon-192.png", 192),
     ("icon-512.png", 512), ("icon-maskable-512.png", 512)],
)
def test_png_icons_exist_at_their_stated_size(name, size):
    assert _png_size(ICONS / name) == (size, size)


def test_the_svg_icon_is_drop_bars_with_a_wrench_head_amber_on_charcoal():
    svg = (ICONS / "icon.svg").read_text()

    assert re.search(r'<rect width="512" height="512" rx="\d+" fill="#1b1e25"/>', svg)  # charcoal tile
    assert svg.count('stroke="#FFA800"') == 1 and svg.count('fill="#FFA800"') == 1  # bars + wrench head
    assert svg.count("<path") == 2  # the two halves of the bar
    assert svg.count("<circle") == 2 and svg.count("<rect") == 2  # wrench head and its open jaw
    assert not re.search(r"https?://(?!www\.w3\.org/2000/svg)", svg) and "<script" not in svg and "<image" not in svg


def test_the_manifest_describes_the_app_and_points_at_real_icons():
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text())

    assert manifest["name"] == "BikeMaint" and manifest["short_name"] == "BikeMaint"
    assert manifest["start_url"] == "/" and manifest["display"] == "standalone"
    assert manifest["theme_color"].lower() == "#ffa800" and manifest["background_color"].lower() == "#1b1e25"
    sizes = {(i["sizes"], i.get("purpose", "any")) for i in manifest["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= sizes
    for icon in manifest["icons"]:
        path = STATIC / icon["src"].removeprefix("/static/")
        assert path.exists(), icon["src"]
        side = int(icon["sizes"].split("x")[0])
        assert _png_size(path) == (side, side)


@pytest.mark.parametrize("path", ["/login", "/"])
def test_pages_declare_the_icons_manifest_and_theme_colour(signed_in_client, client, path):
    page = (client if path == "/login" else signed_in_client).get(path).text

    assert re.search(r'<link rel="icon" href="[^"]*/static/icons/icon\.svg" type="image/svg\+xml">', page)
    assert re.search(r'<link rel="icon" href="[^"]*/static/icons/favicon-32\.png" sizes="32x32" type="image/png">', page)
    assert re.search(r'<link rel="apple-touch-icon" href="[^"]*/static/icons/apple-touch-icon\.png">', page)
    assert re.search(r'<link rel="manifest" href="[^"]*/static/manifest\.webmanifest">', page)
    assert re.search(r'<meta name="theme-color" content="#f2f4f8" media="\(prefers-color-scheme: light\)">', page)
    assert re.search(r'<meta name="theme-color" content="#1b1e25" media="\(prefers-color-scheme: dark\)">', page)


@pytest.mark.parametrize(
    "path,kind",
    [("/static/icons/icon.svg", "image/svg+xml"), ("/static/icons/icon-192.png", "image/png"),
     ("/static/icons/apple-touch-icon.png", "image/png"), ("/static/manifest.webmanifest", "manifest+json")],
)
def test_icon_assets_are_served_without_signing_in(client, path, kind):
    response = client.get(path)

    assert response.status_code == 200 and kind in response.headers["content-type"]


def test_the_icon_budget_stays_small():
    assert sum(p.stat().st_size for p in ICONS.iterdir()) < 100 * 1024
