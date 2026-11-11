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
