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
    offered: bool = True  # False = legacy kind: still valid on existing parts, never offered


def _kind(type_: str, label: str, parents, multi: bool = False, offered: bool = True) -> ComponentKind:
    return ComponentKind(type_, label, None if parents is None else frozenset(parents), multi, offered)


# What the rider tracks mileage on (specs/005-unified-bike-screen): a short, meaningful list.
_OFFERED: tuple[ComponentKind, ...] = (
    _kind("frame", "frame", {BIKE}),
    _kind("fork", "fork", {BIKE}),
    _kind("wheel", "wheel", {BIKE}, multi=True),  # a wheel or a wheelset; front and rear allowed
    _kind("tire", "tire", {"wheel", "rim"}),
    _kind("brake", "brake", {BIKE}, multi=True),
    _kind("drivetrain", "drivetrain", {BIKE}),
    _kind("chain", "chain", {BIKE, "drivetrain"}),
    _kind("pedal", "pedal", {BIKE, "crankset"}),
    _kind("saddle", "saddle", {BIKE}),
    _kind("handlebar", "handlebar", {BIKE}),
    _kind("other", "other part", None, multi=True),
)

# Finer kinds from feature 004: kept so existing parts keep working, but never offered.
_LEGACY: tuple[ComponentKind, ...] = (
    _kind("hub", "hub", {"wheel"}, offered=False),
    _kind("rim", "rim", {"wheel"}, offered=False),
    _kind("spoke", "spoke", {"wheel"}, multi=True, offered=False),
    _kind("cassette", "cassette", {"hub"}, offered=False),
    _kind("rotor", "rotor", {"hub"}, offered=False),
    _kind("crankset", "crankset", {BIKE, "drivetrain"}, offered=False),
    _kind("derailleur", "derailleur", {BIKE, "drivetrain"}, offered=False),
    _kind("shifter", "shifter", {BIKE, "handlebar"}, multi=True, offered=False),
    _kind("pad", "pad", {BIKE, "brake"}, multi=True, offered=False),
    _kind("stem", "stem", {BIKE}, offered=False),
    _kind("seatpost", "seatpost", {BIKE}, offered=False),
    _kind("bolt", "bolt", None, multi=True, offered=False),
)

COMPONENT_KINDS: dict[str, ComponentKind] = {k.type: k for k in (*_OFFERED, *_LEGACY)}
COMPONENT_TYPES: tuple[str, ...] = tuple(k.type for k in _OFFERED)  # what UIs and creates offer
ALL_COMPONENT_TYPES: tuple[str, ...] = tuple(COMPONENT_KINDS)  # includes legacy kinds
MULTI_INSTANCE_COMPONENT_TYPES: frozenset[str] = frozenset(
    k.type for k in COMPONENT_KINDS.values() if k.multi
)


def is_offered(component_type: str) -> bool:
    kind = COMPONENT_KINDS.get(component_type)
    return kind is not None and kind.offered


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
    shown = [p for p in kind.parents if p == BIKE or is_offered(p)] or list(kind.parents)
    allowed = sorted(shown, key=lambda p: (p != BIKE, p))
    label = kind.label
    article = "An" if label[0] in "aeiou" else "A"
    return (
        f"{article} {label} can be mounted on {_join([_noun(p) for p in allowed])}, "
        f"not on {_noun(parent_kind)}."
    )


def can_mount(component_type: str, parent_kind: str | None) -> bool:
    return placement_error(component_type, parent_kind) is None


def child_types_for(parent_kind: str | None) -> list[str]:
    """Offered component types that may be mounted on `parent_kind`, in display order."""
    return [t for t in COMPONENT_TYPES if can_mount(t, parent_kind)]


def parent_types_for(component_type: str) -> list[str]:
    """Parent kinds (`BIKE` first, then component types in catalog order) that accept the type."""
    parents = [BIKE, *ALL_COMPONENT_TYPES]
    return [p for p in parents if can_mount(component_type, p)]
