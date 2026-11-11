"""The component kind catalog and placement rules (specs/005-unified-bike-screen, M1)."""

import pytest

from app.models import component_kinds as kinds
from app.models.component_kinds import BIKE

OFFERED = ["frame", "fork", "wheel", "tire", "brake", "drivetrain", "chain", "pedal", "saddle",
           "handlebar", "other"]
LEGACY = {"hub", "rim", "spoke", "cassette", "rotor", "crankset", "derailleur", "shifter", "pad",
          "stem", "seatpost", "bolt"}


def test_offered_kinds_are_the_short_meaningful_list_in_order():
    assert list(kinds.COMPONENT_TYPES) == OFFERED
    assert len(kinds.COMPONENT_TYPES) <= 11


def test_older_finer_kinds_stay_valid_but_are_never_offered():
    assert LEGACY == set(kinds.ALL_COMPONENT_TYPES) - set(kinds.COMPONENT_TYPES)
    for legacy in LEGACY:
        assert kinds.COMPONENT_KINDS[legacy].offered is False
        assert not kinds.is_offered(legacy)
    assert all(kinds.is_offered(t) for t in OFFERED)
    assert not kinds.is_offered("flux-capacitor")


def test_wheels_brakes_and_other_allow_several_everything_else_is_single():
    assert {"wheel", "brake", "other"} <= kinds.MULTI_INSTANCE_COMPONENT_TYPES
    for single in ("frame", "fork", "tire", "drivetrain", "chain", "pedal", "saddle", "handlebar"):
        assert single not in kinds.MULTI_INSTANCE_COMPONENT_TYPES
    assert {"spoke", "bolt", "pad", "shifter"} <= kinds.MULTI_INSTANCE_COMPONENT_TYPES  # legacy


def test_every_kind_has_a_label_and_parents_that_exist():
    for kind in kinds.COMPONENT_KINDS.values():
        assert kind.label
        for parent in kind.parents or ():
            assert parent == BIKE or parent in kinds.COMPONENT_KINDS


@pytest.mark.parametrize(
    "child,parent",
    [
        ("frame", BIKE), ("fork", BIKE), ("wheel", BIKE), ("brake", BIKE), ("drivetrain", BIKE),
        ("pedal", BIKE), ("saddle", BIKE), ("handlebar", BIKE), ("chain", BIKE),
        ("tire", "wheel"), ("chain", "drivetrain"), ("other", BIKE), ("other", "wheel"),
        ("other", "tire"),
        # older arrangements keep working
        ("tire", "rim"), ("rim", "wheel"), ("hub", "wheel"), ("spoke", "wheel"),
        ("cassette", "hub"), ("pedal", "crankset"), ("bolt", "wheel"), ("pad", "brake"),
    ],
)
def test_valid_placements(child, parent):
    assert kinds.placement_error(child, parent) is None
    assert kinds.can_mount(child, parent)


@pytest.mark.parametrize(
    "child,parent",
    [
        ("pedal", "wheel"), ("pedal", "tire"), ("tire", BIKE), ("tire", "brake"), ("wheel", "wheel"),
        ("wheel", "tire"), ("frame", "wheel"), ("brake", "wheel"), ("saddle", "handlebar"),
        ("chain", "wheel"), ("handlebar", "frame"), ("rim", BIKE),
    ],
)
def test_invalid_placements_are_refused(child, parent):
    assert kinds.placement_error(child, parent) is not None
    assert not kinds.can_mount(child, parent)


def test_error_message_names_what_is_allowed_and_what_was_tried():
    assert kinds.placement_error("pedal", "wheel") == "A pedal can be mounted on the bike, not on a wheel."
    assert kinds.placement_error("tire", BIKE) == "A tire can be mounted on a wheel, not on the bike."
    assert kinds.placement_error("chain", "wheel") == (
        "A chain can be mounted on the bike or a drivetrain, not on a wheel."
    )


def test_messages_never_suggest_hidden_kinds():
    for child in OFFERED:
        message = kinds.placement_error(child, "tire") or ""
        for legacy in LEGACY:
            assert legacy not in message, (child, message)


def test_storage_is_always_allowed():
    for component_type in kinds.ALL_COMPONENT_TYPES:
        assert kinds.placement_error(component_type, None) is None


def test_unknown_types_are_refused():
    assert kinds.placement_error("flux-capacitor", BIKE) is not None


def test_child_and_parent_type_helpers_offer_only_current_kinds():
    assert kinds.child_types_for("wheel") == ["tire", "other"]
    assert kinds.child_types_for("drivetrain") == ["chain", "other"]
    assert set(kinds.child_types_for(BIKE)) == set(OFFERED) - {"tire"}
    assert kinds.child_types_for("tire") == ["other"]
    assert kinds.parent_types_for("tire") == ["wheel", "rim"]
    assert kinds.parent_types_for("pedal") == [BIKE, "crankset"]
    assert "wheel" in kinds.parent_types_for("other")
