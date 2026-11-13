"""Versioned static addresses (specs/020-free-placement-and-categories, FR-014)."""

import re

from app.services import asset_service


def _write(directory, name, text):
    (directory / name).write_text(text)


def test_the_address_carries_a_version_token(tmp_path):
    _write(tmp_path, "styles.css", "a{}")

    url = asset_service.static_url("styles.css", static_dir=tmp_path)

    assert re.fullmatch(r"/static/styles\.css\?v=[0-9a-f]{8,}", url)


def test_the_token_is_stable_while_the_content_is_unchanged(tmp_path):
    _write(tmp_path, "builder.js", "let a = 1;")

    first = asset_service.static_url("builder.js", static_dir=tmp_path)
    second = asset_service.static_url("builder.js", static_dir=tmp_path)

    assert first == second


def test_the_token_changes_when_the_content_changes(tmp_path):
    _write(tmp_path, "builder.js", "let a = 1;")
    before = asset_service.static_url("builder.js", static_dir=tmp_path)

    _write(tmp_path, "builder.js", "let a = 2;")  # same size, different content
    after = asset_service.static_url("builder.js", static_dir=tmp_path)

    assert before != after


def test_a_missing_file_still_gives_a_plain_address(tmp_path):
    assert asset_service.static_url("nope.css", static_dir=tmp_path) == "/static/nope.css"
