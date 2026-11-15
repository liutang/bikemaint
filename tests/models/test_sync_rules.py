"""The sync-rule matcher (specs/060-sync-rules)."""

import pytest

from app.models import sync_rules as rules


def _match(sports="", ride_types="", keywords="", sport=None, ride_type=None, name=None):
    return rules.ride_matches(sports, ride_types, keywords, sport, ride_type, name)


def test_an_empty_rule_matches_everything():
    assert _match(sport="Run", ride_type="race", name="x") and _match()


def test_each_filter_must_match_when_filled_in():
    assert _match(sports="Ride,GravelRide", sport="GravelRide")
    assert not _match(sports="Ride", sport="VirtualRide")
    assert not _match(sports="Ride", ride_types="race", sport="Ride", ride_type="default")
    assert _match(sports="Ride", ride_types="race,workout", sport="Ride", ride_type="workout")


def test_any_one_keyword_in_the_name_matches_ignoring_case():
    assert _match(keywords="commute, zwift", name="Morning COMMUTE to work")
    assert not _match(keywords="commute, zwift", name="Sunday long ride")


def test_unknown_details_match_so_nothing_disappears_silently():
    assert _match(sports="Ride", ride_types="race", keywords="x")  # sport, type and name all unknown
    assert _match(sports="Ride", sport=None)


def test_parse_and_clean_inputs():
    assert rules.clean_keywords(" Commute ,, zwift , commute") == "commute,zwift"
    assert rules.clean_keywords("") == ""
    with pytest.raises(ValueError):
        rules.clean_keywords("x" * 201)
    with pytest.raises(ValueError):
        rules.clean_keywords(",".join(f"k{i}" for i in range(11)))
    assert rules.clean_choices(["Ride", "GravelRide"], rules.SPORTS) == "Ride,GravelRide"
    with pytest.raises(ValueError):
        rules.clean_choices(["Swim"], rules.SPORTS)
    assert rules.ride_type_of(None) == "default" and rules.ride_type_of(10) == "default"
    assert rules.ride_type_of(11) == "race" and rules.ride_type_of(12) == "workout"
