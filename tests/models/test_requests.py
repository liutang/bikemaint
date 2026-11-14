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


from app.models.requests import MaintenanceLogRequest  # noqa: E402


@pytest.mark.parametrize("value", ["00:00", "09:05", "14:30", "23:59"])
def test_maintenance_time_accepts_hh_mm(value):
    assert MaintenanceLogRequest(service_type="Topup", performed_at="2026-05-01", performed_time=value).performed_time == value


def test_maintenance_time_is_optional_and_blank_means_none():
    assert MaintenanceLogRequest(service_type="Topup", performed_at="2026-05-01").performed_time is None
    assert MaintenanceLogRequest(service_type="Topup", performed_at="2026-05-01", performed_time="").performed_time is None


@pytest.mark.parametrize("value", ["24:00", "12:60", "9:5", "noon", "12:30:00", "<b>"])
def test_maintenance_time_rejects_anything_else(value):
    with pytest.raises(ValidationError):
        MaintenanceLogRequest(service_type="Topup", performed_at="2026-05-01", performed_time=value)


@pytest.mark.parametrize("value,ok", [("1:30", True), ("0:45", True), ("99:59", True), ("", True),
                                      ("0:00", False), ("1:75", False), ("abc", False), ("100:00", False)])
def test_a_ride_moving_time_is_h_mm_or_blank(value, ok):
    from app.models.requests import RideRequest

    def build():
        return RideRequest(ride_date="2026-09-02", miles=5, moving_time=value)

    if ok:
        assert build().moving_time == (value or None)
    else:
        with pytest.raises(ValidationError):
            build()
