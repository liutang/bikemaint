"""The categorised palette as rendered (specs/020-free-placement-and-categories, US2)."""

import re
from pathlib import Path

from app.models import component_kinds
from app.services import bike_service, component_service


def _bike():
    return bike_service.create_bike(name="Road")


def _mk(name, component_type, **parent):
    return component_service.create_component(name=name, component_type=component_type, **parent)


def test_five_collapsed_categories_in_order_on_the_bike_screen(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    found = re.findall(r'<details class="palette-category"([^>]*)>\s*<summary>([^<]*)</summary>', html)
    assert [name for _, name in found] == list(component_kinds.CATEGORIES)
    assert all("open" not in attrs for attrs, _ in found)  # all collapsed on load


def test_each_category_lists_its_parts_by_name_in_order(signed_in_client):
    bike = _bike()
    html = signed_in_client.get(f"/bikes/{bike.id}").text

    blocks = re.split(r'<details class="palette-category"', html)[1:]
    for block, (category, kinds) in zip(blocks, component_kinds.offered_by_category()):
        names = re.findall(r'<span class="side-name">([^<]*)</span>', block)
        assert names == [k.name for k in kinds], category


def test_every_palette_part_is_a_drag_source_with_its_type(signed_in_client):
    bike = _bike()

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    types = re.findall(r'draggable="true" data-source="palette" data-type="([a-z_]+)"', html)
    assert types == list(component_kinds.COMPONENT_TYPES)


def test_the_same_palette_shows_on_a_part_screen(signed_in_client):
    bike = _bike()
    wheel = _mk("Wheel", "wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    assert html.count('<details class="palette-category"') == 5


def test_chips_and_the_part_page_use_the_kind_display_name(signed_in_client):
    bike = _bike()
    lever = _mk("Left lever", "shifter", parent_bike_id=bike.id)
    spare = _mk("Spare", "wheelset")

    assert '<span class="chip">Shift levers</span>' in signed_in_client.get(f"/bikes/{bike.id}").text
    assert "Shift levers" in signed_in_client.get(f"/components/{lever.id}").text
    assert '<span class="chip">Wheel Set</span>' in signed_in_client.get("/components").text
    assert spare.id


def test_a_part_of_an_older_kind_still_shows_with_a_readable_name(signed_in_client):
    bike = _bike()
    _mk("Old drivetrain", "drivetrain", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/bikes/{bike.id}").text

    assert "Old drivetrain" in html and '<span class="chip">Drivetrain</span>' in html


def test_the_category_header_is_a_native_disclosure_so_it_works_by_keyboard(signed_in_client):
    html = signed_in_client.get(f"/bikes/{_bike().id}").text

    assert "<summary>Brakes</summary>" in html  # <details>/<summary> is keyboard operable and announced
    css = (Path("app/static") / "styles.css").read_text()
    assert ".palette-category" in css
