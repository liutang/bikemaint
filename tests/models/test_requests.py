"""Boundary validation for the theme choice (specs/003-cockpit-theme, FR-021)."""

import pytest
from pydantic import ValidationError

from app.models.requests import ThemeSettingsRequest


@pytest.mark.parametrize("value", ["system", "light", "dark"])
def test_accepts_only_the_three_themes(value):
    assert ThemeSettingsRequest(theme=value).theme == value


@pytest.mark.parametrize("value", ["", "DARK", "blue", "<script>", "dark; Path=/"])
def test_rejects_anything_else(value):
    with pytest.raises(ValidationError):
        ThemeSettingsRequest(theme=value)


from app.models.requests import BikeCatalogRequest  # noqa: E402


def test_bike_catalog_request_accepts_slugs_and_the_keep_marker():
    assert BikeCatalogRequest(catalog_id="trek-domane").manual_baseline_mileage == 0
    assert BikeCatalogRequest(catalog_id="__keep__", manual_baseline_mileage=5).catalog_id == "__keep__"


@pytest.mark.parametrize("bad", ["", "Trek Domane", "trek_domane", "x" * 65, "a;b", "<b>"])
def test_bike_catalog_request_rejects_malformed_ids(bad):
    with pytest.raises(ValidationError):
        BikeCatalogRequest(catalog_id=bad)


def test_bike_catalog_request_rejects_negative_mileage():
    with pytest.raises(ValidationError):
        BikeCatalogRequest(catalog_id="trek-domane", manual_baseline_mileage=-1)
