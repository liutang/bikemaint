"""Shared layout rules (specs/071-ui-consistency US1, US2)."""

import re

CSS = open("app/static/styles.css").read()


def _rule(selector):
    """Every declaration block whose selector list contains `selector` exactly, joined."""
    selector = selector.rstrip(" {")
    plain = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    bodies = [body for sels, body in re.findall(r"([^{}]+)\{([^{}]*)\}", plain)
              if selector in [s.strip() for s in sels.split(",")]]
    assert bodies, selector
    return " ".join(bodies)


def test_buttons_in_forms_keep_their_natural_width():
    assert "justify-self: start" in _rule(".form > .btn")


def test_number_date_and_time_fields_and_drop_downs_are_sized_to_their_values():
    assert "max-width" in _rule('.field input[type="number"]')
    assert "max-width" in _rule('.field input[type="date"]')
    assert "width: auto" in _rule(".field select")


def test_forms_and_fields_cannot_push_the_page_sideways():
    assert "minmax(0, 1fr)" in _rule(".form {")
    assert "minmax(0, 1fr)" in _rule(".field {")


def test_card_grid_is_two_columns_on_wide_screens_and_one_on_narrow_ones():
    grid = _rule(".card-grid {")
    assert "auto-fit" in grid and "min(100%" in grid and "align-items: stretch" in grid
    assert "grid-column: 1 / -1" in _rule(".card-grid > .panel.wide")


def test_checkboxes_and_radios_keep_their_size_when_their_label_wraps():
    """specs/079 T037 (branch 080): a two-line label must not squeeze its bubble or box."""
    assert "flex-shrink: 0" in _rule('input[type="radio"]')
    assert "flex-shrink: 0" in _rule('input[type="checkbox"]')


def test_the_sync_dot_no_longer_takes_its_own_row_on_phones():
    """specs/084 US2 scenario 3."""
    phone = re.search(r"@media \(max-width: 40rem\) \{(.*?)\n\}", CSS, re.S).group(1)
    assert ".sync-status" not in phone
