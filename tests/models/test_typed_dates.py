"""The year rule for typed dates (specs/076 research §1)."""

import pytest
from pydantic_core import PydanticCustomError

from app.models.typed_dates import full_year


@pytest.mark.parametrize(
    ("typed", "read"),
    [
        ("0026-07-17", "2026-07-17"),
        ("0000-07-17", "2000-07-17"),
        ("0099-12-31", "2099-12-31"),
        ("0024-02-29", "2024-02-29"),
        ("1900-01-01", "1900-01-01"),
        ("2026-11-18", "2026-11-18"),
    ],
)
def test_short_years_mean_20yy_and_others_are_kept(typed, read):
    assert full_year(typed) == read


@pytest.mark.parametrize("typed", ["0100-01-01", "0202-03-01", "1899-12-31"])
def test_years_from_100_to_1899_are_refused(typed):
    with pytest.raises(PydanticCustomError) as exc:
        full_year(typed)
    assert str(exc.value) == "Enter a valid date"


@pytest.mark.parametrize("typed", ["", "July 17", "2026-7-17", None, 20260717])
def test_other_text_is_passed_through_for_the_field_to_report(typed):
    assert full_year(typed) == typed
