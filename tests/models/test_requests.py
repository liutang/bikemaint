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
