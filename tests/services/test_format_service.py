"""Thousands separators for displayed mileage (specs/059-comma-mileage)."""

import pytest

from app.services import format_service


@pytest.mark.parametrize(
    "value,one,zero",
    [(0, "0.0", "0"), (548.34, "548.3", "548"), (1991, "1,991.0", "1,991"), (12345.67, "12,345.7", "12,346"),
     (1234567.8, "1,234,567.8", "1,234,568"), (-1500.2, "-1,500.2", "-1,500")],
)
def test_one_and_no_decimal_formats(value, one, zero):
    assert format_service.num1(value) == one
    assert format_service.num0(value) == zero


def test_blank_values_stay_blank():
    assert format_service.num1(None) == "" and format_service.num0(None) == ""


@pytest.mark.parametrize("value,text", [(1000, "1,000"), (186, "186"), (2.5, "2.5"), (1500.0, "1,500"), (1234.5, "1,234.5")])
def test_counts_drop_a_trailing_zero_but_keep_separators(value, text):
    assert format_service.count(value) == text
