"""Typed-name confirmation for destructive actions (specs/029-safe-bike-delete).

The rider must type a phrase (a bike's full name) exactly before it is deleted. The browser
compares the text with an HTML `pattern`; the server compares again, so the server is the authority.
Callable without FastAPI or request objects.
"""

from __future__ import annotations

import re

# Only regular-expression syntax characters are escaped: browsers reject other, unnecessary
# escapes (such as "\ " or "\-") in a pattern attribute and would then ignore it.
_SYNTAX_CHARACTERS = re.compile(r"([\\^$.*+?()\[\]{}|/])")


def phrase_matches(expected: str, typed: str | None) -> bool:
    """True only when the typed text equals the expected phrase exactly (case, spacing, length)."""
    return typed is not None and typed == expected


def html_pattern(expected: str) -> str:
    """A pattern attribute value that the browser matches against the whole field: exactly `expected`."""
    return _SYNTAX_CHARACTERS.sub(r"\\\1", expected)
