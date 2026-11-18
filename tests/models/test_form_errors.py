import pytest
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.models.form_errors import error_context, field_errors, message_context


class Sample(BaseModel):
    name: str = Field(min_length=1)
    count: int = Field(ge=0)

    @model_validator(mode="after")
    def _cross_field(self):
        if self.name == "boom":
            raise ValueError("Model-level problem")
        return self


def _error(**data) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        Sample(**data)
    return caught.value


def test_field_errors_maps_each_field_to_its_message():
    errors = field_errors(_error(name="", count=-1))

    assert set(errors) == {"name", "count"}
    assert "at least 1" in errors["name"]
    assert "greater than or equal to 0" in errors["count"]


def test_only_the_first_message_per_field_is_kept():
    errors = field_errors(_error(name="", count="abc"))

    assert isinstance(errors["count"], str)


def test_model_level_errors_stay_out_of_the_field_map():
    exc = _error(name="boom", count=1)

    assert field_errors(exc) == {}
    assert error_context({"name": "boom"}, exc)["errors"] == ["Value error, Model-level problem"]


def test_error_context_bundles_summary_field_errors_and_entered_values():
    exc = _error(name="", count=3)

    context = error_context({"name": "", "count": "3"}, exc)

    assert context["values"] == {"name": "", "count": "3"}
    assert list(context["field_errors"]) == ["name"]
    assert len(context["errors"]) == 1


def test_message_context_for_non_pydantic_errors():
    context = message_context({"delta_miles": "abc"}, "Enter a number.", field="delta_miles")

    assert context == {
        "errors": ["Enter a number."],
        "field_errors": {"delta_miles": "Enter a number."},
        "values": {"delta_miles": "abc"},
    }
    assert message_context({"a": "1"}, "Oops")["field_errors"] == {}


# ------------------------------------------------ specs/076 FR-005: refused forms show four-digit years

from app.models.form_errors import message_context  # noqa: E402


def test_refused_forms_show_two_digit_years_as_four_digits():
    form = {"installed_date": "0026-03-01", "removed_date": "0026-04-01", "ride_date": "0026-07-17",
            "performed_at": "0000-01-05", "note": "0026-01-01"}
    values = message_context(form, "That overlaps another period.")["values"]
    assert values["installed_date"] == "2026-03-01"
    assert values["removed_date"] == "2026-04-01"
    assert values["ride_date"] == "2026-07-17"
    assert values["performed_at"] == "2000-01-05"
    assert values["note"] == "0026-01-01"  # not a date field


def test_a_refused_year_is_shown_as_typed():
    values = message_context({"ride_date": "0202-03-01"}, "Enter a valid date")["values"]
    assert values["ride_date"] == "0202-03-01"
