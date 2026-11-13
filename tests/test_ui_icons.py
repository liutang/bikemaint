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


# ------------------------------------------------ recognizable bike and part icons (specs/006, M2)

import re  # noqa: E402

PART_ICONS = ["frame", "fork", "wheel", "tire", "rotor", "brake", "drivetrain", "chain", "pedal",
              "saddle", "handlebar"]
OFFERED_TYPES = PART_ICONS + ["other"]
LEGACY_TYPES = ["hub", "rim", "spoke", "cassette", "crankset", "derailleur", "shifter", "pad", "stem",
                "seatpost", "bolt"]


def _render(env, call):
    macro = call.split("(")[0]
    return env.from_string("{% from 'partials/icons.html' import " + macro + " %}{{ " + call + " }}").render()


@pytest.mark.parametrize("name", PART_ICONS)
def test_each_part_has_its_own_decorative_icon(env, name):
    html = _render(env, f"{name}()")

    assert html.lstrip().startswith("<svg") and 'aria-hidden="true"' in html and 'focusable="false"' in html


def test_all_part_icons_are_different_drawings(env):
    drawings = {name: re.search(r">(.*)</svg>", _render(env, f"{name}()"), re.S).group(1) for name in PART_ICONS}

    assert len(set(drawings.values())) == len(PART_ICONS)


def test_the_bike_icon_is_a_bike_with_two_wheels_a_frame_a_saddle_and_handlebars(env):
    html = _render(env, "bike()")

    assert html.count("<circle") == 2  # the wheels
    paths = " ".join(re.findall(r'<path d="([^"]+)"', html))
    assert "H" in paths and paths.count("M") >= 4  # frame tubes, saddle and handlebar strokes


@pytest.mark.parametrize("part_type", OFFERED_TYPES + LEGACY_TYPES)
def test_the_part_macro_picks_an_icon_for_every_known_type(env, part_type):
    html = env.from_string("{% from 'partials/icons.html' import part %}{{ part('" + part_type + "', 'icon part-icon') }}").render()

    assert html.lstrip().startswith("<svg") and 'class="icon part-icon"' in html


def test_the_part_macro_maps_each_offered_type_to_its_own_icon(env):
    def draw(t):
        return env.from_string("{% from 'partials/icons.html' import part %}{{ part('" + t + "') }}").render()

    assert len({draw(t) for t in OFFERED_TYPES}) == len(OFFERED_TYPES)
    assert draw("rim") == draw("tire") and draw("hub") == draw("wheel")  # older kinds borrow


def test_unknown_types_fall_back_to_the_generic_part_icon(env):
    unknown = env.from_string("{% from 'partials/icons.html' import part %}{{ part('flux-capacitor') }}").render()
    other = env.from_string("{% from 'partials/icons.html' import part %}{{ part('other') }}").render()

    assert unknown == other


def test_every_catalog_kind_renders_an_icon_with_the_wrench_as_the_fallback():
    from app.models import component_kinds
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    macro = env.get_template("partials/icons.html").module.part
    for kind in component_kinds.ALL_COMPONENT_TYPES:
        assert str(macro(kind, "icon")).strip().startswith("<svg"), kind
    assert str(macro("not-a-kind", "icon")) == str(macro("lights", "icon"))  # both fall back to the wrench
