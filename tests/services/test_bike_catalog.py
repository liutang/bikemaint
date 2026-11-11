"""The curated catalog of common bikes (specs/004-bike-builder, FR-001/FR-002)."""

import re

import pytest

from app.services import bike_catalog

CATEGORIES = {"road", "gravel", "mountain", "hybrid", "e-bike"}


def test_catalog_is_a_substantial_curated_list():
    assert len(bike_catalog.all_entries()) >= 50


def test_every_category_is_represented():
    assert {e.category for e in bike_catalog.all_entries()} == CATEGORIES


def test_ids_are_unique_url_safe_slugs():
    ids = [e.id for e in bike_catalog.all_entries()]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i) for i in ids)


def test_display_names_are_unique_make_and_model():
    names = [bike_catalog.display_name(e) for e in bike_catalog.all_entries()]
    assert len(names) == len(set(names))
    entry = bike_catalog.get("trek-domane")
    assert bike_catalog.display_name(entry) == "Trek Domane"
    assert entry.category == "road"


def test_get_returns_none_for_unknown_or_malformed_ids():
    for value in ("", "nope", "TREK-DOMANE", "trek-domane; DROP TABLE bike", None):
        assert bike_catalog.get(value) is None


def test_grouped_lists_categories_then_makes_alphabetically():
    groups = bike_catalog.grouped()

    assert [label for label, _ in groups] == ["Road", "Gravel", "Mountain", "Hybrid", "E-bike"]
    for _, entries in groups:
        keys = [(e.make, e.model) for e in entries]
        assert keys == sorted(keys)
    assert sum(len(entries) for _, entries in groups) == len(bike_catalog.all_entries())


@pytest.mark.parametrize("category", sorted(CATEGORIES))
def test_each_category_has_several_models_from_several_makes(category):
    entries = [e for e in bike_catalog.all_entries() if e.category == category]
    assert len(entries) >= 6
    assert len({e.make for e in entries}) >= 4
