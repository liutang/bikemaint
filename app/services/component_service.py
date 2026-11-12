"""Business logic for components: creation, nesting validation (FR-024), moves, and
recursive soft-delete of an installed sub-tree.

Per Constitution Principle II this module is callable without FastAPI/request objects;
`app/routers/components.py` only translates HTTP concerns to/from these functions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db import maintenance as maintenance_db
from app.db import mileage as mileage_db
from app.db import schedules as schedules_db
from app.db.connection import get_connection
from app.models import component_kinds
from app.services import component_history_service as history_service
from app.models.component_kinds import BIKE, MULTI_INSTANCE_COMPONENT_TYPES
from app.models.rows import Component


class ComponentNestingConflictError(Exception):
    """Raised when installing a component would violate FR-024's single-instance rule."""


class ComponentPlacementError(ComponentNestingConflictError):
    """Raised when a component type cannot be mounted on the chosen parent (specs/004, FR-006)."""


@dataclass(frozen=True)
class MoveTarget:
    """A place a component may legally go: `bike:ID`, `component:ID` or `storage`."""

    value: str
    label: str


def _entity(conn, *, bike_id: int | None, component_id: int | None):
    return (
        bikes_db.get_by_id(conn, bike_id)
        if bike_id is not None
        else components_db.get_by_id(conn, component_id)
    )


def _log_event(
    conn: sqlite3.Connection,
    *,
    bike_id: int | None = None,
    component_id: int | None = None,
    description: str,
) -> None:
    """Record an automatic parts event (added/removed) in the history of a bike or a part."""
    entity = _entity(conn, bike_id=bike_id, component_id=component_id)
    if entity is None:
        return
    now = _now()
    maintenance_db.create(
        conn,
        bike_id=bike_id,
        component_id=component_id,
        description=description,
        performed_at=now[:10],
        mileage_at_service=entity.total_mileage,
        kind="event",
    )


def _parent_name(
    conn: sqlite3.Connection, parent_bike_id: int | None, parent_component_id: int | None
) -> str | None:
    parent = _entity(conn, bike_id=parent_bike_id, component_id=parent_component_id)
    return parent.name if parent is not None else None


def _log_added(
    conn: sqlite3.Connection,
    component: Component,
    parent_bike_id: int | None,
    parent_component_id: int | None,
) -> None:
    """"Added X (type)" on the parent and "Installed on P" on the part itself."""
    name = _parent_name(conn, parent_bike_id, parent_component_id)
    if name is None:
        return
    _log_event(
        conn,
        bike_id=parent_bike_id,
        component_id=parent_component_id,
        description=f"Added {component.name} ({component.component_type})",
    )
    _log_event(conn, component_id=component.id, description=f"Installed on {name}")


def _log_removed(
    conn: sqlite3.Connection,
    component: Component,
    parent_bike_id: int | None,
    parent_component_id: int | None,
) -> None:
    """"Removed X (type)" on the old parent and "Removed from P" on the part itself."""
    name = _parent_name(conn, parent_bike_id, parent_component_id)
    if name is None:
        return
    _log_event(
        conn,
        bike_id=parent_bike_id,
        component_id=parent_component_id,
        description=f"Removed {component.name} ({component.component_type})",
    )
    _log_event(conn, component_id=component.id, description=f"Removed from {name}")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parent_kind(
    conn: sqlite3.Connection, *, parent_bike_id: int | None, parent_component_id: int | None
) -> str | None:
    if parent_bike_id is not None:
        return BIKE
    if parent_component_id is not None:
        parent = components_db.get_by_id(conn, parent_component_id)
        if parent is None:
            raise LookupError(f"No component with id {parent_component_id}")
        return parent.component_type
    return None


def _validate_placement(
    conn: sqlite3.Connection,
    *,
    component_type: str,
    parent_bike_id: int | None,
    parent_component_id: int | None,
) -> None:
    kind = _parent_kind(conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id)
    message = component_kinds.placement_error(component_type, kind)
    if message:
        raise ComponentPlacementError(message)


def _validate_nesting(
    conn: sqlite3.Connection,
    *,
    component_type: str,
    parent_bike_id: int | None,
    parent_component_id: int | None,
    exclude_component_id: int | None,
) -> None:
    if parent_bike_id is None and parent_component_id is None:
        return  # storage always allowed
    _validate_placement(
        conn,
        component_type=component_type,
        parent_bike_id=parent_bike_id,
        parent_component_id=parent_component_id,
    )
    if component_type in MULTI_INSTANCE_COMPONENT_TYPES:
        return
    siblings = components_db.list_children(
        conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
    )
    for sibling in siblings:
        if sibling.id == exclude_component_id:
            continue
        if sibling.component_type == component_type:
            raise ComponentNestingConflictError(
                f"A {component_type} is already installed there."
            )


def _resolve_top_bike_id(
    conn: sqlite3.Connection, *, parent_bike_id: int | None, parent_component_id: int | None
) -> int | None:
    if parent_bike_id is not None:
        return parent_bike_id
    if parent_component_id is not None:
        return components_db.resolve_top_bike_id(conn, parent_component_id)
    return None


def get_component(component_id: int) -> Component | None:
    with get_connection() as conn:
        return components_db.get_by_id(conn, component_id)


def list_in_storage() -> list[Component]:
    with get_connection() as conn:
        return components_db.list_in_storage(conn)


def get_tree_for_bike(bike_id: int) -> list[Component]:
    with get_connection() as conn:
        return components_db.get_tree_for_bike(conn, bike_id)


def get_descendants(component_id: int) -> list[Component]:
    with get_connection() as conn:
        return components_db.get_descendants(conn, component_id)


def build_tree(roots: list[Component], all_components: list[Component]) -> list[dict]:
    """Group a flat component list into nested `{"component", "children"}` dicts for templates."""
    children_by_parent_id: dict[int, list[Component]] = {}
    for component in all_components:
        if component.parent_component_id is not None:
            children_by_parent_id.setdefault(component.parent_component_id, []).append(component)

    def _node(component: Component) -> dict:
        return {
            "component": component,
            "children": [_node(child) for child in children_by_parent_id.get(component.id, [])],
        }

    return [_node(root) for root in roots]


def create_component(
    *,
    name: str,
    component_type: str,
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
    manual_baseline_mileage: float = 0.0,
    installed_at: str | None = None,
) -> Component:
    """Create a component; when mounted, `installed_at` (default now) opens its first period."""
    if installed_at is not None:
        history_service.check_not_future(installed_at)
    with get_connection() as conn:
        _validate_nesting(
            conn,
            component_type=component_type,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
            exclude_component_id=None,
        )
        component = components_db.create(
            conn,
            name=name,
            component_type=component_type,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
            manual_baseline_mileage=manual_baseline_mileage,
        )
        if parent_bike_id is not None or parent_component_id is not None:
            top_bike_id = _resolve_top_bike_id(
                conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
            )
            components_db.open_installation_period(
                conn,
                component.id,
                parent_bike_id=top_bike_id,
                parent_component_id=parent_component_id,
                installed_at=installed_at or _now(),
            )
            _log_added(conn, component, parent_bike_id, parent_component_id)
            if installed_at is not None:
                # Back-dated: rides since then already belong to this part.
                mileage_db.recompute_component_total_mileage(conn, component.id)
                component = components_db.get_by_id(conn, component.id)
        return component


def update_component(
    component_id: int, *, name: str, component_type: str, manual_baseline_mileage: float
) -> Component:
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")
        if component_type != component.component_type:
            if not component_kinds.is_offered(component_type):
                raise ComponentPlacementError(f"{component_type} is not an available part type.")
            for child in components_db.list_children(conn, parent_component_id=component_id):
                message = component_kinds.placement_error(child.component_type, component_type)
                if message:
                    raise ComponentPlacementError(
                        f"Changing the type would leave a {child.component_type} without a valid "
                        f"parent. {message}"
                    )
            _validate_nesting(
                conn,
                component_type=component_type,
                parent_bike_id=component.parent_bike_id,
                parent_component_id=component.parent_component_id,
                exclude_component_id=component_id,
            )
        mileage_earned_beyond_baseline = component.total_mileage - component.manual_baseline_mileage
        new_total_mileage = mileage_earned_beyond_baseline + manual_baseline_mileage
        return components_db.update(
            conn,
            component_id,
            name=name,
            component_type=component_type,
            manual_baseline_mileage=manual_baseline_mileage,
            total_mileage=new_total_mileage,
        )


def valid_types_for_parent(
    *, parent_bike_id: int | None = None, parent_component_id: int | None = None
) -> list[str]:
    """Component types that may be added under the given parent (all types for storage)."""
    with get_connection() as conn:
        try:
            kind = _parent_kind(
                conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
            )
        except LookupError:
            kind = None
        return component_kinds.child_types_for(kind)


@dataclass(frozen=True)
class _Slot:
    """A parent a part could be mounted on: the bike itself or one of its components."""

    value: str  # "bike:ID" | "component:ID"
    label: str
    kind: str  # BIKE or a component type
    children: list[Component]
    component_id: int | None = None


def _scope_slots(conn: sqlite3.Connection, root: str | None) -> list[_Slot]:
    """Every parent inside `root` (`bike:ID` or `component:ID`); all bikes when root is None."""
    slots: list[_Slot] = []

    def _tree_slots(prefix: str, tree: list[Component], top: list[Component]) -> list[_Slot]:
        by_id = {c.id: c for c in tree}
        children_of: dict[int | None, list[Component]] = {}
        for c in tree:
            children_of.setdefault(c.parent_component_id, []).append(c)

        def _path(c: Component) -> str:
            names = []
            node: Component | None = c
            while node is not None and node.id in by_id:
                names.append(node.name)
                node = by_id.get(node.parent_component_id)
            return " › ".join([prefix, *reversed(names)]) if prefix else " › ".join(reversed(names))

        return [
            _Slot(f"component:{c.id}", _path(c), c.component_type, children_of.get(c.id, []), c.id)
            for c in tree
        ]

    kind, _, raw = (root or "").partition(":")
    if root is None or kind == "bike":
        for bike in bikes_db.list_active(conn):
            if root is not None and bike.id != int(raw):
                continue
            tree = components_db.get_tree_for_bike(conn, bike.id)
            slots.append(
                _Slot(
                    f"bike:{bike.id}",
                    bike.name,
                    BIKE,
                    components_db.list_children(conn, parent_bike_id=bike.id),
                )
            )
            slots.extend(_tree_slots(bike.name, tree, []))
    elif kind == "component":
        top = components_db.get_by_id(conn, int(raw))
        if top is not None:
            tree = [top, *components_db.get_descendants(conn, top.id)]
            slots.extend(_tree_slots("", tree, [top]))
    return slots


def _candidate_targets(
    conn: sqlite3.Connection,
    component_type: str,
    *,
    exclude_id: int | None = None,
    blocked: frozenset[int] = frozenset(),
    skip_parent: tuple[int | None, int | None] = (None, None),
    root: str | None = None,
) -> list[MoveTarget]:
    """Bikes and components inside `root` where a part of `component_type` could be mounted now."""
    multi = component_type in MULTI_INSTANCE_COMPONENT_TYPES
    skip_bike_id, skip_component_id = skip_parent
    targets: list[MoveTarget] = []
    for slot in _scope_slots(conn, root):
        if slot.component_id is not None and slot.component_id in blocked:
            continue
        if slot.value == f"bike:{skip_bike_id}" and skip_bike_id is not None:
            continue
        if slot.component_id is not None and slot.component_id == skip_component_id:
            continue
        if not component_kinds.can_mount(component_type, slot.kind):
            continue
        if not multi and any(
            c.id != exclude_id and c.component_type == component_type for c in slot.children
        ):
            continue
        targets.append(MoveTarget(slot.value, slot.label))
    return targets


def list_type_targets(
    component_type: str, *, bike_id: int | None = None, root: str | None = None
) -> list[MoveTarget]:
    """Places inside a bike (or `root`) where a *new* part of `component_type` could be mounted."""
    scope = root if root is not None else (f"bike:{bike_id}" if bike_id is not None else None)
    with get_connection() as conn:
        return _candidate_targets(conn, component_type, root=scope)


def list_move_targets(
    component_id: int, *, only_bike_id: int | None = None, root: str | None = None
) -> list[MoveTarget]:
    """Every place `component_id` could be moved right now, and only those (specs/004, FR-014)."""
    scope = root if root is not None else (f"bike:{only_bike_id}" if only_bike_id is not None else None)
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")
        blocked = frozenset(
            {component_id} | {d.id for d in components_db.get_descendants(conn, component_id)}
        )
        targets = _candidate_targets(
            conn,
            component.component_type,
            exclude_id=component_id,
            blocked=blocked,
            skip_parent=(component.parent_bike_id, component.parent_component_id),
            root=scope,
        )
        if component.parent_bike_id is not None or component.parent_component_id is not None:
            targets.append(MoveTarget("storage", "Storage"))
        return targets


def _check_before(
    conn: sqlite3.Connection,
    before_component_id: int | None,
    *,
    parent_bike_id: int | None,
    parent_component_id: int | None,
) -> None:
    if before_component_id is None:
        return
    siblings = components_db.list_children(
        conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
    )
    if all(c.id != before_component_id for c in siblings):
        raise ValueError("That position is not under the chosen parent.")


def mount_new_component(
    component_type: str,
    *,
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
    before_component_id: int | None = None,
    installed_at: str | None = None,
) -> Component:
    """Create a part of `component_type` (default name) mounted on a parent, optionally ordered."""
    kind = component_kinds.COMPONENT_KINDS.get(component_type)
    if kind is None or not kind.offered:
        raise ComponentPlacementError(f"{component_type} is not an available part type.")
    with get_connection() as conn:
        _check_before(
            conn,
            before_component_id,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
        )
    component = create_component(
        name=kind.label.capitalize(),
        component_type=component_type,
        parent_bike_id=parent_bike_id,
        parent_component_id=parent_component_id,
        installed_at=installed_at,
    )
    if before_component_id is not None:
        with get_connection() as conn:
            components_db.reorder(conn, component.id, before_component_id=before_component_id)
            component = components_db.get_by_id(conn, component.id)
    return component


def move_component(
    component_id: int,
    *,
    parent_bike_id: int | None = None,
    parent_component_id: int | None = None,
    before_component_id: int | None = None,
) -> Component:
    """Move a component (with its sub-tree) to a parent, optionally just before a sibling there.

    Moving onto its current parent only re-orders it (last, or before `before_component_id`);
    installation periods and mileage attribution are untouched in that case.
    """
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")

        _check_before(
            conn,
            before_component_id,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
        )
        if (component.parent_bike_id, component.parent_component_id) == (
            parent_bike_id,
            parent_component_id,
        ):
            components_db.reorder(conn, component_id, before_component_id=before_component_id)
            moved = components_db.get_by_id(conn, component_id)
            assert moved is not None
            return moved

        if parent_component_id is not None:
            if parent_component_id == component_id:
                raise ValueError("A component cannot be installed inside itself.")
            descendant_ids = {d.id for d in components_db.get_descendants(conn, component_id)}
            if parent_component_id in descendant_ids:
                raise ValueError(
                    "A component cannot be moved into its own installed sub-tree."
                )

        _validate_nesting(
            conn,
            component_type=component.component_type,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
            exclude_component_id=component_id,
        )

        now = _now()
        components_db.close_open_installation_period(conn, component_id, removed_at=now)
        # Events use the part as it was before the move (its old parent) and as it is after.
        _log_removed(conn, component, component.parent_bike_id, component.parent_component_id)
        components_db.set_parent(
            conn,
            component_id,
            parent_bike_id=parent_bike_id,
            parent_component_id=parent_component_id,
        )
        _log_added(conn, component, parent_bike_id, parent_component_id)

        new_top_bike_id = _resolve_top_bike_id(
            conn, parent_bike_id=parent_bike_id, parent_component_id=parent_component_id
        )
        if parent_bike_id is not None or parent_component_id is not None:
            components_db.open_installation_period(
                conn,
                component_id,
                parent_bike_id=new_top_bike_id,
                parent_component_id=parent_component_id,
                installed_at=now,
            )

        # The moved sub-tree's own internal nesting is unchanged, but its denormalized
        # top-bike (used for mileage attribution rollup) has — re-cycle each descendant's
        # installation period so future syncs attribute rides to the correct bike.
        for descendant in components_db.get_descendants(conn, component_id):
            components_db.close_open_installation_period(conn, descendant.id, removed_at=now)
            components_db.open_installation_period(
                conn,
                descendant.id,
                parent_bike_id=new_top_bike_id,
                parent_component_id=descendant.parent_component_id,
                installed_at=now,
            )

        if before_component_id is not None:
            components_db.reorder(conn, component_id, before_component_id=before_component_id)
        moved = components_db.get_by_id(conn, component_id)
        assert moved is not None
        return moved


def detach_to_storage(
    conn: sqlite3.Connection,
    component_id: int,
    *,
    removed_at: str,
    deleted_parent_name: str | None = None,
) -> None:
    """Move a component (with its own sub-tree) to storage on an open connection.

    Shared by `delete_component` and `bike_service.delete_bike`: what was installed in
    something that goes away is kept, not deleted. Rides stop accruing to it from now on.
    """
    if deleted_parent_name is not None:
        _log_event(
            conn,
            component_id=component_id,
            description=f"Removed from {deleted_parent_name} (deleted)",
        )
    components_db.close_open_installation_period(conn, component_id, removed_at=removed_at)
    components_db.set_parent(conn, component_id, parent_bike_id=None, parent_component_id=None)
    for descendant in components_db.get_descendants(conn, component_id):
        components_db.close_open_installation_period(conn, descendant.id, removed_at=removed_at)
        components_db.open_installation_period(
            conn,
            descendant.id,
            parent_bike_id=None,
            parent_component_id=descendant.parent_component_id,
            installed_at=removed_at,
        )


class ConfirmationRequiredError(Exception):
    """Raised when deleting a component with an installed sub-tree needs confirmation."""


def delete_component(component_id: int, *, confirmed: bool = False) -> None:
    """Delete a part. Its sub-parts are kept: they move to storage with their own sub-trees."""
    with get_connection() as conn:
        component = components_db.get_by_id(conn, component_id)
        if component is None:
            raise LookupError(f"No component with id {component_id}")
        children = components_db.list_children(conn, parent_component_id=component_id)
        if children and not confirmed:
            raise ConfirmationRequiredError(
                "Its sub-parts will move to storage; confirm to delete it."
            )
        has_history_or_schedule = maintenance_db.has_entries_for_component(
            conn, component_id
        ) or schedules_db.has_active_for_component(conn, component_id)
        if has_history_or_schedule and not confirmed:
            raise ConfirmationRequiredError(
                "It has maintenance history or an active schedule; confirm to delete it."
            )
        now = _now()
        for child in children:
            detach_to_storage(conn, child.id, removed_at=now, deleted_parent_name=component.name)
        _log_removed(conn, component, component.parent_bike_id, component.parent_component_id)
        components_db.close_open_installation_period(conn, component_id, removed_at=now)
        components_db.soft_delete(conn, component_id)
