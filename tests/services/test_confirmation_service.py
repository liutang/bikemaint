"""Typed-name confirmation (specs/029-safe-bike-delete)."""

import re

import pytest

from app.services import confirmation_service


@pytest.mark.parametrize("typed", ["2023 Trek Madone"])
def test_the_exact_name_matches(typed):
    assert confirmation_service.phrase_matches("2023 Trek Madone", typed)


@pytest.mark.parametrize(
    "typed",
    ["", "2023 trek madone", "2023 Trek Madone ", " 2023 Trek Madone", "2023  Trek Madone",
     "2023 Trek Madon", "2023 Trek Madone SLR", None],
)
def test_anything_else_does_not_match(typed):
    assert not confirmation_service.phrase_matches("2023 Trek Madone", typed)


NAMES = [
    "2023 Trek Madone",
    "2023 Trek Madone SLR (Disc) 7.0",
    "Bob's C++ [fast] {x} | a/b \\ ^$",
    "100% Café - Ünïcode?",
]


@pytest.mark.parametrize("name", NAMES)
def test_the_html_pattern_accepts_exactly_the_name(name):
    pattern = confirmation_service.html_pattern(name)

    assert re.fullmatch(pattern, name)
    assert not re.fullmatch(pattern, name + "x")
    assert not re.fullmatch(pattern, " " + name)
    assert not re.fullmatch(pattern, name.lower() if name.lower() != name else name + " ")


@pytest.mark.parametrize("name", NAMES)
def test_the_pattern_only_escapes_regular_expression_syntax_characters(name):
    pattern = confirmation_service.html_pattern(name)

    # every backslash in the pattern precedes one of the syntax characters, so it is a legal escape
    # in a browser's pattern attribute (which rejects unnecessary escapes such as "\ " or "\-")
    for escaped in re.findall(r"\\(.)", pattern):
        assert escaped in "\\^$.*+?()[]{}|/", escaped
