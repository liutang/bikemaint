"""Collapsible parts and the drag gap in the builder (specs/073-builder-drag-collapse).

The markup is checked here; the script and CSS are checked statically. The drag and
collapse behavior itself is verified in a browser (quickstart.md)."""

import re
from pathlib import Path

from app.services import bike_service, component_service

STATIC = Path(__file__).parent.parent / "app" / "static"
JS = (STATIC / "builder.js").read_text()
CSS = (STATIC / "styles.css").read_text()


def _mk(name, kind, **parent):
    return component_service.create_component(name=name, component_type=kind, **parent)


def _row(html, component_id):
    match = re.search(
        rf'<div class="node-row drop-target"[^>]*data-id="{component_id}"[^>]*>(.*?)<span class="node-actions">',
        html, re.S)
    assert match, f"no row for {component_id}"
    return match.group(1)


def _tree(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    wheelset = _mk("Roval wheelset", "wheelset", parent_bike_id=bike.id)
    front = _mk("Front wheel", "wheel", parent_component_id=wheelset.id)
    tire = _mk("Front tire", "tire", parent_component_id=front.id)
    rear = _mk("Rear wheel", "wheel", parent_component_id=wheelset.id)
    _mk("Rear tire", "tire", parent_component_id=rear.id)
    html = signed_in_client.get(f"/bikes/{bike.id}").text
    return html, wheelset, front, tire


def test_a_part_with_sub_parts_has_a_chevron_button_and_a_count(signed_in_client):
    html, wheelset, front, _ = _tree(signed_in_client)

    row = _row(html, wheelset.id)
    button = re.search(r'<button class="twisty"[^>]*>', row).group(0)
    assert 'type="button"' in button  # FR-010: without scripts it submits nothing
    assert 'aria-expanded="true"' in button
    assert 'aria-label="Collapse Roval wheelset"' in button and 'title="Hide sub-parts"' in button
    assert row.index('class="twisty"') < row.index('class="drag-handle"')
    assert re.search(r'<span class="sub-count">4 parts</span>', row)
    assert re.search(r'<span class="sub-count">1 part</span>', _row(html, front.id))


def test_a_part_without_sub_parts_has_an_equal_spacer_and_no_count(signed_in_client):
    html, _, _, tire = _tree(signed_in_client)

    row = _row(html, tire.id)
    assert '<span class="twisty-space" aria-hidden="true"></span>' in row
    assert "twisty\"" not in row.replace("twisty-space", "") and "sub-count" not in row


def _rule(selector):
    """The body of the first rule whose selector list includes `selector`."""
    css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        if selector in [part.strip() for part in match.group(1).split(",")]:
            return match.group(2)
    raise AssertionError(f"no CSS rule for {selector}")


def test_collapse_is_toggled_by_the_script_and_remembered_in_this_browser():
    assert "is-collapsed" in JS and "aria-expanded" in JS and "aria-label" in JS
    assert '"bikemaint.collapsed"' in JS and "localStorage" in JS
    # every storage access is guarded, so a blocked storage just shows everything open
    for use in re.finditer(r"localStorage\.\w+", JS):
        before = JS[max(0, use.start() - 40):use.start()]
        assert "try" in before, f"unguarded {use.group(0)}"
    assert "htmx:afterSwap" in JS


def test_collapsed_styles_hide_sub_parts_but_not_a_drop_gap():
    assert "display: none" in _rule(".sub-count")
    assert "display: inline" in _rule(".builder-node.is-collapsed > .node-row .sub-count")
    assert "display: none" in _rule(".builder-node.is-collapsed > ul.builder-nodes > li:not(.drop-slot)")
    sizes = re.search(r"\.twisty,\s*\.twisty-space\s*\{([^}]*)\}", CSS).group(1)
    assert "width:" in sizes and "height:" in sizes


def test_the_drag_gap_lifts_the_part_and_glides_rows_without_innerhtml():
    assert "drop-slot" in JS and "is-lifted" in JS and "slot-where" in JS
    assert "innerHTML" not in JS and "createElement" in JS
    assert ".animate(" in JS and "getAnimations" in JS
    assert re.search(r"ZONE\s*=\s*0\.3\b", JS) and "0.12" in JS
    assert len(JS.encode()) <= 16 * 1024


def test_collapsed_parts_open_after_a_hover_and_on_a_drop_inside():
    assert re.search(r"setTimeout\([^;]*?700\)", JS, re.S) or "700)" in JS
    assert "springOpen" in JS


def test_every_class_the_new_script_sets_is_styled():
    for cls in ("is-dragging", "is-lifted", "is-over", "is-valid", "is-collapsed", "is-closing",
                "drop-slot", "slot-row", "slot-where", "twisty"):
        assert cls in JS, f"script never uses {cls}"
        assert f".{cls}" in CSS, f"no CSS for .{cls}"
    for cls in ("sub-count", "twisty-space"):  # server-rendered, styled
        assert f".{cls}" in CSS
