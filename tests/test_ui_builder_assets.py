"""Static checks for the drag-and-drop script and its contract with the templates
(specs/004-bike-builder, M3, FR-019). The drag behavior itself is verified in a browser."""

import re
from pathlib import Path

import pytest

from app.services import bike_service, component_service

STATIC = Path(__file__).parent.parent / "app" / "static"
JS = (STATIC / "builder.js").read_text()


def test_script_is_served_as_javascript(signed_in_client):
    response = signed_in_client.get("/static/builder.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_script_is_small_hand_written_and_dependency_free():
    assert len(JS.encode()) <= 12 * 1024
    assert not re.search(r"https?://", JS)
    assert not re.search(r"\b(eval|document\.write|innerHTML|import\s|require\()", JS)
    assert JS.lstrip().startswith("(") and '"use strict"' in JS


def test_script_talks_only_to_the_builder_endpoints_through_htmx():
    assert "/build/move" in JS and "/build/add" in JS
    assert "htmx.ajax" in JS
    assert "htmx:beforeSwap" in JS  # lets 422 reasons replace the builder instead of being dropped
    assert "fetch(" not in JS and "XMLHttpRequest" not in JS


def test_every_data_attribute_the_script_reads_is_emitted_by_the_builder_markup(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="W", component_type="wheel", parent_bike_id=bike.id)
    component_service.create_component(name="S", component_type="spoke", parent_component_id=wheel.id)
    component_service.create_component(name="Spare", component_type="saddle")
    html = signed_in_client.get(f"/bikes/{bike.id}/build").text

    def attr(name):  # dataset.fooBar -> data-foo-bar
        return "data-" + re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), name)

    read = {attr(n) for n in re.findall(r"dataset\.([A-Za-z]+)", JS)}
    assert {"data-source", "data-id", "data-type", "data-ref", "data-parent-ref", "data-accepts",
            "data-bike-id"} <= read
    for name in read:
        assert f'{name}="' in html, f"markup never emits {name}"


def test_every_class_the_script_toggles_is_styled():
    css = (STATIC / "styles.css").read_text()
    for cls in ("is-valid", "is-invalid", "is-over", "is-dragging"):
        assert cls in JS
        assert f".{cls}" in css, f"no CSS for .{cls}"


def test_builder_styles_stack_panes_on_narrow_screens_and_respect_reduced_motion():
    css = (STATIC / "styles.css").read_text()
    assert ".builder-panes" in css
    match = re.search(r"@media \(max-width: 6\d(?:\.\d+)?rem\)\s*\{[^@]*\.builder-panes", css, re.S)
    assert match, "builder panes must stack on narrow screens"
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_drag_handles_and_controls_meet_the_tap_target_size():
    css = (STATIC / "styles.css").read_text()
    rule = re.search(r"\.btn-icon\s*\{([^}]*)\}", css)
    assert rule and "min-width: var(--tap-min)" in rule.group(1)
