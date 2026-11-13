"""The component kind catalog (specs/020-free-placement-and-categories): names, categories, no rules."""

from app.models import component_kinds as kinds

CATEGORIES = {
    "Accessories": ["Accessories", "Apparel", "Computer", "Lights"],
    "Brakes": ["Brake", "Brake Cable", "Brake Lever", "Brake Pads", "Rotor"],
    "Drivetrain": ["Bottom Bracket", "Cassette", "Chain", "Chainrings", "Crankset", "Derailleur",
                   "Pedals", "Shift levers", "Shifter Cable"],
    "Frame": ["Fork", "Frame", "Handlebar", "Handlebar Tape", "Headset", "Saddle", "Seatpost",
              "Shock", "Stem"],
    "Wheels": ["Axle", "Hub", "Trainer", "Tube", "Tire", "Wheel", "Wheel Set"],
}
LEGACY = {"drivetrain", "other", "rim", "spoke", "bolt"}
NEW_IDS = {"accessories", "apparel", "computer", "lights", "brake_cable", "brake_lever",
           "bottom_bracket", "chainrings", "shifter_cable", "handlebar_tape", "headset", "shock",
           "axle", "trainer", "tube", "wheelset"}


def test_categories_are_in_the_supplied_order():
    assert list(kinds.CATEGORIES) == list(CATEGORIES)


def test_each_category_offers_exactly_the_supplied_parts_in_order():
    grouped = {name: [k.name for k in items] for name, items in kinds.offered_by_category()}
    assert grouped == CATEGORIES
    assert sum(len(v) for v in grouped.values()) == 34


def test_offered_types_are_exactly_the_catalog_parts():
    offered = [k.type for _, items in kinds.offered_by_category() for k in items]
    assert list(kinds.COMPONENT_TYPES) == offered
    assert NEW_IDS <= set(offered)
    assert len(set(offered)) == 34


def test_older_kinds_not_in_the_list_stay_valid_but_are_never_offered():
    assert LEGACY == set(kinds.ALL_COMPONENT_TYPES) - set(kinds.COMPONENT_TYPES)
    for legacy in LEGACY:
        assert not kinds.is_offered(legacy)
    assert not kinds.is_offered("flux-capacitor")


def test_existing_kinds_show_the_supplied_names():
    assert kinds.kind_name("pedal") == "Pedals"
    assert kinds.kind_name("shifter") == "Shift levers"
    assert kinds.kind_name("pad") == "Brake Pads"
    assert kinds.kind_name("wheelset") == "Wheel Set"
    assert kinds.kind_name("drivetrain") == "Drivetrain"  # legacy kinds still have a name
    assert kinds.kind_name("not-a-kind") == "not-a-kind"  # unknown ids are shown as they are


def test_placement_rules_and_the_one_per_parent_limit_are_gone():
    for gone in ("placement_error", "can_mount", "child_types_for", "parent_types_for",
                 "MULTI_INSTANCE_COMPONENT_TYPES"):
        assert not hasattr(kinds, gone)
