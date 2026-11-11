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


from app.models.requests import BikeDetailsRequest  # noqa: E402


def test_bike_details_accepts_valid_entries_and_trims_text():
    request = BikeDetailsRequest(year="2022", make="  Trek ", model=" Domane SL ", category="road")

    assert (request.year, request.make, request.model, request.category) == (2022, "Trek", "Domane SL", "road")
    assert request.manual_baseline_mileage == 0


def test_blank_details_become_none_so_a_legacy_bike_can_keep_its_name():
    request = BikeDetailsRequest(year="", make="  ", model="", category="other")

    assert (request.year, request.make, request.model) == (None, None, None)


@pytest.mark.parametrize("year", ["abc", "1899", "-5", "3000", "20.5"])
def test_bike_details_reject_bad_years(year):
    with pytest.raises(ValidationError):
        BikeDetailsRequest(year=year, make="Trek", model="Domane", category="road")


def test_bike_details_accept_next_years_model():
    from datetime import date

    assert BikeDetailsRequest(year=date.today().year + 1, make="T", model="M", category="road")


@pytest.mark.parametrize("category", ["", "BMX", "spaceship", "road; drop"])
def test_bike_details_reject_unknown_categories(category):
    with pytest.raises(ValidationError):
        BikeDetailsRequest(year=2022, make="Trek", model="Domane", category=category)


@pytest.mark.parametrize("category", ["road", "gravel", "mountain", "hybrid", "e-bike", "other"])
def test_bike_details_accept_every_category(category):
    assert BikeDetailsRequest(year=2022, make="Trek", model="Domane", category=category).category == category


def test_bike_details_reject_overlong_text_and_negative_mileage():
    with pytest.raises(ValidationError):
        BikeDetailsRequest(year=2022, make="x" * 61, model="Domane", category="road")
    with pytest.raises(ValidationError):
        BikeDetailsRequest(year=2022, make="Trek", model="Domane", category="road", manual_baseline_mileage=-1)
