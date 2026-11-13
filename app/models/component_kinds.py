"""Component kind catalog: which parts exist, what they are called and how the palette groups them.

Pure reference data plus small helpers, importable anywhere (no framework, no DB). It is the single
source of truth for the part vocabulary (specs/020-free-placement-and-categories). Any part may be
placed under any parent or the bike, so there are no placement rules here; the rider is the mechanic.
A kind is *offered* (listed in the palette) or *legacy* (valid on existing parts, never offered).
"""

from __future__ import annotations

from dataclasses import dataclass

BIKE = "bike"

CATEGORIES: tuple[str, ...] = ("Accessories", "Brakes", "Drivetrain", "Frame", "Wheels")


@dataclass(frozen=True)
class ComponentKind:
    type: str  # the id stored on the part
    name: str  # what the rider sees
    category: str | None = None  # palette group; None for legacy kinds
    offered: bool = True


def _group(category: str, *kinds: tuple[str, str]) -> tuple[ComponentKind, ...]:
    return tuple(ComponentKind(type_, name, category) for type_, name in kinds)


# Exactly the parts the rider asked for, in the order they asked for them.
_OFFERED: tuple[ComponentKind, ...] = (
    *_group(
        "Accessories",
        ("accessories", "Accessories"), ("apparel", "Apparel"), ("computer", "Computer"),
        ("lights", "Lights"),
    ),
    *_group(
        "Brakes",
        ("brake", "Brake"), ("brake_cable", "Brake Cable"), ("brake_lever", "Brake Lever"),
        ("pad", "Brake Pads"), ("rotor", "Rotor"),
    ),
    *_group(
        "Drivetrain",
        ("bottom_bracket", "Bottom Bracket"), ("cassette", "Cassette"), ("chain", "Chain"),
        ("chainrings", "Chainrings"), ("crankset", "Crankset"), ("derailleur", "Derailleur"),
        ("pedal", "Pedals"), ("shifter", "Shift levers"), ("shifter_cable", "Shifter Cable"),
    ),
    *_group(
        "Frame",
        ("fork", "Fork"), ("frame", "Frame"), ("handlebar", "Handlebar"),
        ("handlebar_tape", "Handlebar Tape"), ("headset", "Headset"), ("saddle", "Saddle"),
        ("seatpost", "Seatpost"), ("shock", "Shock"), ("stem", "Stem"),
    ),
    *_group(
        "Wheels",
        ("axle", "Axle"), ("hub", "Hub"), ("trainer", "Trainer"), ("tube", "Tube"),
        ("tire", "Tire"), ("wheel", "Wheel"), ("wheelset", "Wheel Set"),
    ),
)

# Older kinds that are not in the palette: kept so existing parts keep working, never offered.
_LEGACY: tuple[ComponentKind, ...] = (
    ComponentKind("drivetrain", "Drivetrain", offered=False),
    ComponentKind("other", "Other part", offered=False),
    ComponentKind("rim", "Rim", offered=False),
    ComponentKind("spoke", "Spoke", offered=False),
    ComponentKind("bolt", "Bolt", offered=False),
)

COMPONENT_KINDS: dict[str, ComponentKind] = {k.type: k for k in (*_OFFERED, *_LEGACY)}
COMPONENT_TYPES: tuple[str, ...] = tuple(k.type for k in _OFFERED)  # what UIs and creates offer
ALL_COMPONENT_TYPES: tuple[str, ...] = tuple(COMPONENT_KINDS)  # includes legacy kinds


def is_offered(component_type: str) -> bool:
    kind = COMPONENT_KINDS.get(component_type)
    return kind is not None and kind.offered


def kind_name(component_type: str) -> str:
    """The display name of a kind; an unknown id is shown as it is."""
    kind = COMPONENT_KINDS.get(component_type)
    return kind.name if kind else component_type


def offered_by_category() -> list[tuple[str, list[ComponentKind]]]:
    """The palette: each category with its offered kinds, in display order."""
    return [(c, [k for k in _OFFERED if k.category == c]) for c in CATEGORIES]
