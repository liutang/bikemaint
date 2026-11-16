"""Row actions are icon buttons (specs/071-ui-consistency US4)."""

import re

import pytest

TEMPLATES = ["components/install_history.html", "bikes/install_history.html", "rides/log.html",
             "maintenance/history_list.html", "schedules/owner_list.html", "partials/other_row.html",
             "partials/attention_card.html"]


@pytest.mark.parametrize("path", TEMPLATES)
def test_row_rides_edit_and_delete_are_labelled_icon_buttons(path):
    src = open(f"app/templates/{path}").read()

    assert not re.search(r'class="btn"[^>]*>\s*(Rides|Edit|Delete)\s*<', src)
    for label in re.findall(r'aria-label="(Rides|Edit|Delete)"', src):
        assert f'title="{label}"' in src
    assert 'class="btn btn-icon"' in src


def test_the_route_and_pencil_icons_exist():
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("app/templates"))
    module = env.get_template("partials/icons.html").module
    assert str(module.route()).startswith("<svg") and str(module.edit()).startswith("<svg")
