import pytest
from jinja2 import Environment, FileSystemLoader

from app.main import TEMPLATES_DIR

ICONS = ["warning", "clock", "check", "question", "chevron", "plus", "trash", "bike", "wrench",
         "settings", "sign_out"]


@pytest.fixture
def env():
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


@pytest.mark.parametrize("name", ICONS)
def test_icon_macro_emits_a_decorative_svg(env, name):
    template = env.from_string(
        "{% from 'partials/icons.html' import " + name + " %}{{ " + name + "() }}"
    )

    html = template.render()

    assert html.lstrip().startswith("<svg")
    assert 'aria-hidden="true"' in html
    assert 'focusable="false"' in html


# ------------------------------------------------ part icon pack (specs/069-part-icon-pack)

import re  # noqa: E402

from app.models import component_kinds  # noqa: E402


def _render(env, call):
    macro = call.split("(")[0]
    return env.from_string("{% from 'partials/icons.html' import " + macro + " %}{{ " + call + " }}").render()


def _part(env, kind):
    return _render(env, f"part('{kind}', 'icon part-icon')")


def test_the_bike_icon_is_a_bike_with_two_wheels_a_frame_a_saddle_and_handlebars(env):
    html = _render(env, "bike()")

    assert html.count("<circle") == 2  # the wheels
    paths = " ".join(re.findall(r'<path d="([^"]+)"', html))
    assert "H" in paths and paths.count("M") >= 4  # frame tubes, saddle and handlebar strokes


@pytest.mark.parametrize("kind", component_kinds.ALL_COMPONENT_TYPES)
def test_every_catalog_kind_renders_a_decorative_icon(env, kind):
    html = _part(env, kind)

    assert html.lstrip().startswith("<svg") and 'class="icon part-icon"' in html
    assert 'aria-hidden="true"' in html and 'focusable="false"' in html and 'viewBox="0 0 24 24"' in html


def test_every_offered_kind_has_its_own_drawing(env):
    drawings = {kind: _part(env, kind) for kind in component_kinds.COMPONENT_TYPES}

    assert len(component_kinds.COMPONENT_TYPES) == 35
    assert len(set(drawings.values())) == 35


def test_older_kinds_and_unknown_types_fall_back(env):
    assert _part(env, "rim") == _part(env, "wheel") == _part(env, "spoke")
    assert _part(env, "flux-capacitor") == _part(env, "other")
    assert _part(env, "bolt") not in {_part(env, k) for k in ("other", "wheel")}


@pytest.mark.parametrize("kind", ["brake_lever", "shifter", "derailleur", "chainrings"])
def test_the_approved_solid_icons_are_filled(env, kind):
    assert 'fill="currentColor"' in _part(env, kind)


def test_drivetrain_uses_the_thinner_line_and_icons_are_colored_by_text(env):
    assert 'stroke-width="1.25"' in _part(env, "drivetrain")
    for kind in component_kinds.COMPONENT_TYPES:
        html = _part(env, kind)
        assert "#" not in re.sub(r"&#\d+;", "", html)  # no hard-coded colors: currentColor only


# --- specs/070: nav icons ---

def _inner(html):
    return re.search(r">(.*)</svg>", html, re.S).group(1)


def test_the_maintenance_due_wrench_is_the_part_pack_wrench(env):
    assert _inner(_render(env, "wrench()")) == _inner(_part(env, "other"))
    assert "transform" not in _render(env, "wrench()")


def test_the_settings_icon_is_a_six_tooth_gear_with_a_hole(env):
    html = _render(env, "settings()")
    gear = re.search(r'<path d="(M[^"]+Z)"', html).group(1)

    assert gear.count("L") + 1 == 24  # 6 teeth, 4 corners each
    assert '<circle cx="12" cy="12" r="3"/>' in html and 'stroke-width="2"' in html
