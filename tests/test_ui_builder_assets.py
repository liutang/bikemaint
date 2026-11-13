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
    assert "/builder" in JS and "/move" in JS and "/add" in JS
    assert "htmx.ajax" in JS
    assert "htmx:beforeSwap" in JS  # lets 422 reasons replace the builder instead of being dropped
    assert "fetch(" not in JS and "XMLHttpRequest" not in JS


def test_every_data_attribute_the_script_reads_is_emitted_by_the_builder_markup(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="W", component_type="wheel", parent_bike_id=bike.id)
    component_service.create_component(name="T", component_type="tire", parent_component_id=wheel.id)
    component_service.create_component(name="Spare", component_type="saddle")
    html = signed_in_client.get(f"/bikes/{bike.id}").text

    def attr(name):  # dataset.fooBar -> data-foo-bar
        return "data-" + re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), name)

    read = {attr(n) for n in re.findall(r"dataset\.([A-Za-z]+)", JS)}
    assert {"data-source", "data-id", "data-type", "data-ref", "data-parent-ref",
            "data-root"} <= read
    assert "data-accepts" not in read  # any part can be dropped anywhere (specs/020)
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


def test_breadcrumb_and_part_action_styles_exist_and_wrap_on_small_screens():
    css = (STATIC / "styles.css").read_text()
    assert ".breadcrumb" in css and ".breadcrumb li[aria-current" in css
    assert re.search(r"\.breadcrumb ol\s*\{[^}]*flex-wrap: wrap", css, re.S)
    assert ".part-actions" in css


def test_breadcrumb_markup_is_an_ordered_list_with_the_current_page_marked(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="W", component_type="wheel", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/components/{wheel.id}").text

    nav = re.search(r'<nav class="breadcrumb" aria-label="Breadcrumb">\s*<ol>.*?</ol>\s*</nav>', html, re.S).group(0)
    assert nav.count("<li") == 3 and nav.count('aria-current="page"') == 1
    assert nav.rstrip().endswith("</nav>")


def test_script_lets_palette_parts_be_dropped_on_the_storage_box():
    assert re.search(r'ref === "storage"\) return drag\.source !== "storage"', JS)


def test_the_browser_local_time_script_is_gone_because_the_saved_zone_is_used(signed_in_client):
    assert not (STATIC / "localtime.js").exists()
    assert signed_in_client.get("/static/localtime.js").status_code == 404


def test_the_delete_button_is_styled_unavailable_until_the_name_matches():
    css = (STATIC / "styles.css").read_text()

    rule = re.search(r"\.delete-confirm:has\(input:invalid\) \.btn-danger \{(.*?)\}", css, re.S).group(1)
    assert "pointer-events: none" in rule and "opacity" in rule and "not-allowed" in rule


def test_the_sync_dot_uses_neon_green_and_bright_red_tokens_in_both_themes():
    css = (STATIC / "styles.css").read_text()

    # theme independent, so defined once on :root; a thin ring keeps the dot visible on a light bar
    assert css.count("--sync-ok: #39ff14") == 1 and css.count("--sync-error: #ff1744") == 1
    assert re.search(r"\.sync-status\.sync-ok::before \{[^}]*var\(--sync-ok\)", css)
    assert re.search(r"\.sync-status\.sync-error::before \{[^}]*var\(--sync-error\)", css)
    assert re.search(r"\.sync-status\.sync-off::before \{[^}]*var\(--text-muted\)", css)
    base = re.search(r"\.sync-status::before \{(.*?)\}", css, re.S).group(1)
    assert "var(--success)" not in base  # the dark green that looked black is gone
