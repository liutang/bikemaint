"""The component kind catalog and placement rules (specs/004-bike-builder, M2, FR-005..FR-008)."""

import pytest

from app.models import component_kinds as kinds
from app.models.component_kinds import BIKE


def test_vocabulary_keeps_every_existing_type_and_adds_the_new_parts():
    existing = {"frame", "wheel", "hub", "rim", "tire", "spoke", "bolt", "pad", "drivetrain",
                "chain", "brake", "other"}
    added = {"fork", "cassette", "rotor", "crankset", "pedal", "derailleur", "shifter",
             "handlebar", "stem", "seatpost", "saddle"}
    assert existing | added == set(kinds.COMPONENT_TYPES)
    assert len(kinds.COMPONENT_TYPES) == len(set(kinds.COMPONENT_TYPES))


def test_multi_instance_types_include_the_existing_ones():
    assert {"spoke", "bolt", "pad", "other"} <= kinds.MULTI_INSTANCE_COMPONENT_TYPES
    assert "pedal" in kinds.MULTI_INSTANCE_COMPONENT_TYPES
    assert "wheel" not in kinds.MULTI_INSTANCE_COMPONENT_TYPES


def test_every_kind_has_a_label_and_parents_that_exist():
    for kind in kinds.COMPONENT_KINDS.values():
        assert kind.label
        for parent in kind.parents or ():
            assert parent == BIKE or parent in kinds.COMPONENT_KINDS


@pytest.mark.parametrize(
    "child,parent",
    [
        ("frame", BIKE), ("fork", BIKE), ("wheel", BIKE), ("drivetrain", BIKE), ("brake", BIKE),
        ("handlebar", BIKE), ("stem", BIKE), ("seatpost", BIKE), ("saddle", BIKE),
        ("hub", "wheel"), ("rim", "wheel"), ("spoke", "wheel"), ("tire", "rim"),
        ("cassette", "hub"), ("rotor", "hub"), ("crankset", BIKE), ("crankset", "drivetrain"),
        ("chain", BIKE), ("chain", "drivetrain"), ("derailleur", "drivetrain"),
        ("pedal", "crankset"), ("shifter", "handlebar"), ("pad", "brake"),
        ("bolt", "wheel"), ("bolt", BIKE), ("other", "saddle"), ("other", BIKE),
    ],
)
def test_valid_placements(child, parent):
    assert kinds.placement_error(child, parent) is None
    assert kinds.can_mount(child, parent)


@pytest.mark.parametrize(
    "child,parent",
    [
        ("pedal", "wheel"), ("pedal", BIKE), ("tire", BIKE), ("tire", "wheel"), ("rim", BIKE),
        ("wheel", "rim"), ("wheel", "wheel"), ("frame", "wheel"), ("crankset", "wheel"),
        ("cassette", BIKE), ("saddle", "handlebar"), ("pad", "wheel"), ("chain", "wheel"),
    ],
)
def test_invalid_placements_are_refused(child, parent):
    assert kinds.placement_error(child, parent) is not None
    assert not kinds.can_mount(child, parent)


def test_error_message_names_what_is_allowed_and_what_was_tried():
    assert kinds.placement_error("pedal", "wheel") == "A pedal can be mounted on a crankset, not on a wheel."
    assert kinds.placement_error("tire", BIKE) == "A tire can be mounted on a rim, not on the bike."
    assert kinds.placement_error("crankset", "wheel") == (
        "A crankset can be mounted on the bike or a drivetrain, not on a wheel."
    )


def test_storage_is_always_allowed():
    for component_type in kinds.COMPONENT_TYPES:
        assert kinds.placement_error(component_type, None) is None


def test_unknown_types_are_refused():
    assert kinds.placement_error("flux-capacitor", BIKE) is not None


def test_child_and_parent_type_helpers():
    assert "pedal" in kinds.child_types_for("crankset")
    assert "pedal" not in kinds.child_types_for("wheel")
    assert "tire" in kinds.child_types_for("rim")
    assert {"frame", "wheel", "fork"} <= set(kinds.child_types_for(BIKE))
    assert "tire" not in kinds.child_types_for(BIKE)
    assert kinds.parent_types_for("pedal") == ["crankset"]
    assert set(kinds.parent_types_for("crankset")) == {BIKE, "drivetrain"}
    assert BIKE in kinds.parent_types_for("bolt")  # "anywhere" kinds fit every parent kind
    assert "wheel" in kinds.parent_types_for("bolt")
