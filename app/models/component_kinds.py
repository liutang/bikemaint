"""Component kind catalog: which parts exist and what each may be mounted on.

Pure reference data plus small helpers, importable anywhere (no framework, no DB). It is the single
source of truth for the component vocabulary and the placement rules (specs/004-bike-builder).
A *parent kind* is either `BIKE` or a component type; storage (no parent) always accepts anything.
The rules are a deliberate simplification of a real bike, not an engineering standard.
"""

from __future__ import annotations

from dataclasses import dataclass

BIKE = "bike"


@dataclass(frozen=True)
class ComponentKind:
    type: str
    label: str
    parents: frozenset[str] | None  # None = may be mounted on any parent
    multi: bool = False  # several of this kind may share one parent


def _kind(type_: str, label: str, parents, multi: bool = False) -> ComponentKind:
    return ComponentKind(type_, label, None if parents is None else frozenset(parents), multi)


_KINDS: tuple[ComponentKind, ...] = (
    _kind("frame", "frame", {BIKE}),
    _kind("fork", "fork", {BIKE}),
    _kind("wheel", "wheel", {BIKE}),
    _kind("hub", "hub", {"wheel"}),
    _kind("rim", "rim", {"wheel"}),
    _kind("spoke", "spoke", {"wheel"}, multi=True),
    _kind("tire", "tire", {"rim"}),
    _kind("cassette", "cassette", {"hub"}),
    _kind("rotor", "rotor", {"hub"}),
    _kind("drivetrain", "drivetrain", {BIKE}),
    _kind("crankset", "crankset", {BIKE, "drivetrain"}),
    _kind("pedal", "pedal", {"crankset"}, multi=True),
    _kind("chain", "chain", {BIKE, "drivetrain"}),
    _kind("derailleur", "derailleur", {BIKE, "drivetrain"}),
    _kind("shifter", "shifter", {BIKE, "handlebar"}, multi=True),
    _kind("brake", "brake", {BIKE}),
    _kind("pad", "pad", {BIKE, "brake"}, multi=True),
    _kind("handlebar", "handlebar", {BIKE}),
    _kind("stem", "stem", {BIKE}),
    _kind("seatpost", "seatpost", {BIKE}),
    _kind("saddle", "saddle", {BIKE}),
    _kind("bolt", "bolt", None, multi=True),
    _kind("other", "other part", None, multi=True),
)

COMPONENT_KINDS: dict[str, ComponentKind] = {kind.type: kind for kind in _KINDS}
COMPONENT_TYPES: tuple[str, ...] = tuple(kind.type for kind in _KINDS)
MULTI_INSTANCE_COMPONENT_TYPES: frozenset[str] = frozenset(k.type for k in _KINDS if k.multi)


def _noun(kind: str) -> str:
    """"the bike" or "a wheel" / "an other part" for use in messages."""
    if kind == BIKE:
        return "the bike"
    label = COMPONENT_KINDS[kind].label if kind in COMPONENT_KINDS else kind
    return f"{'an' if label[0] in 'aeiou' else 'a'} {label}"


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} or {parts[-1]}"


def placement_error(component_type: str, parent_kind: str | None) -> str | None:
    """Why `component_type` cannot be mounted on `parent_kind`, or None if it can.

    `parent_kind` is `BIKE`, a component type, or None for storage (always allowed).
    """
    kind = COMPONENT_KINDS.get(component_type)
    if kind is None:
        return f"Unknown component type: {component_type}."
    if parent_kind is None or kind.parents is None or parent_kind in kind.parents:
        return None
    allowed = sorted(kind.parents, key=lambda p: (p != BIKE, p))
    label = kind.label
    article = "An" if label[0] in "aeiou" else "A"
    return (
        f"{article} {label} can be mounted on {_join([_noun(p) for p in allowed])}, "
        f"not on {_noun(parent_kind)}."
    )


def can_mount(component_type: str, parent_kind: str | None) -> bool:
    return placement_error(component_type, parent_kind) is None


def child_types_for(parent_kind: str | None) -> list[str]:
    """Component types that may be mounted on `parent_kind`, in catalog order."""
    return [t for t in COMPONENT_TYPES if can_mount(t, parent_kind)]


def parent_types_for(component_type: str) -> list[str]:
    """Parent kinds (`BIKE` first, then component types in catalog order) that accept the type."""
    parents = [BIKE, *COMPONENT_TYPES]
    return [p for p in parents if can_mount(component_type, p)]
