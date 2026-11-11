"""View model for the interactive bike builder (specs/004-bike-builder, M3).

Pure data assembly on top of the component catalog and `component_service`; importable without
FastAPI. Templates and the drag-and-drop script only render what is computed here, so every
"can this go there?" answer comes from the same rules the server enforces on each request.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.db import bikes as bikes_db
from app.db import components as components_db
from app.db.connection import get_connection
from app.models import component_kinds
from app.models.component_kinds import (
    BIKE,
    COMPONENT_KINDS,
    COMPONENT_TYPES,
    MULTI_INSTANCE_COMPONENT_TYPES,
)
from app.models.rows import Bike, Component
from app.services import component_service
from app.services.component_service import MoveTarget


@dataclass
class BuilderNode:
    component: Component
    ref: str  # "component:ID", the drop-target reference
    parent_ref: str  # "bike:ID" or "component:ID"
    accepts: list[str]  # types that can be dropped *inside* this node right now
    targets: list[MoveTarget]  # keyboard "Move to…" choices on this bike (plus storage)
    can_up: bool = False
    up_before: int | None = None
    can_down: bool = False
    down_before: int | None = None  # None with can_down means "move to the end"
    children: list[BuilderNode] = field(default_factory=list)


@dataclass
class StorageItem:
    component: Component
    targets: list[MoveTarget]


@dataclass
class PaletteItem:
    type: str
    label: str
    targets: list[MoveTarget]


@dataclass
class BuilderView:
    bike: Bike
    root_ref: str
    root_accepts: list[str]
    nodes: list[BuilderNode]
    storage: list[StorageItem]
    palette: list[PaletteItem]


def _accepts(parent_kind: str, children: list[Component]) -> list[str]:
    present = {c.component_type for c in children}
    return [
        t
        for t in component_kinds.child_types_for(parent_kind)
        if t in MULTI_INSTANCE_COMPONENT_TYPES or t not in present
    ]


def build_view(bike_id: int) -> BuilderView | None:
    with get_connection() as conn:
        bike = bikes_db.get_by_id(conn, bike_id)
        if bike is None:
            return None
        tree = components_db.get_tree_for_bike(conn, bike_id)
        storage = components_db.list_in_storage(conn)

    children_of: dict[int | None, list[Component]] = {}
    for c in tree:
        children_of.setdefault(c.parent_component_id, []).append(c)
    top = [c for c in tree if c.parent_bike_id == bike_id]
    bike_ref = f"{BIKE}:{bike_id}"

    def _nodes(siblings: list[Component], parent_ref: str) -> list[BuilderNode]:
        nodes = []
        for index, c in enumerate(siblings):
            kids = children_of.get(c.id, [])
            node = BuilderNode(
                component=c,
                ref=f"component:{c.id}",
                parent_ref=parent_ref,
                accepts=_accepts(c.component_type, kids),
                targets=component_service.list_move_targets(c.id, only_bike_id=bike_id),
                can_up=index > 0,
                up_before=siblings[index - 1].id if index > 0 else None,
                can_down=index < len(siblings) - 1,
                down_before=siblings[index + 2].id if index + 2 < len(siblings) else None,
                children=_nodes(kids, f"component:{c.id}"),
            )
            nodes.append(node)
        return nodes

    return BuilderView(
        bike=bike,
        root_ref=bike_ref,
        root_accepts=_accepts(BIKE, top),
        nodes=_nodes(top, bike_ref),
        storage=[
            StorageItem(c, component_service.list_move_targets(c.id, only_bike_id=bike_id))
            for c in storage
        ],
        palette=[
            PaletteItem(
                type_,
                COMPONENT_KINDS[type_].label.capitalize(),
                component_service.list_type_targets(type_, bike_id=bike_id),
            )
            for type_ in COMPONENT_TYPES
        ],
    )


def _bike_component_ids(bike_id: int) -> set[int]:
    with get_connection() as conn:
        return {c.id for c in components_db.get_tree_for_bike(conn, bike_id)}


def _check_parent_on_bike(bike_id: int, ids: set[int], parents: dict[str, int | None]) -> None:
    on_this_bike = parents["parent_bike_id"] == bike_id or parents["parent_component_id"] in ids
    is_storage = parents["parent_bike_id"] is None and parents["parent_component_id"] is None
    if not (on_this_bike or is_storage):
        raise ValueError("That place is not on this bike.")


def add_part(
    bike_id: int,
    component_type: str,
    parents: dict[str, int | None],
    before_component_id: int | None = None,
) -> Component:
    """Create a new part from the palette on this bike; placement rules come from the catalog."""
    ids = _bike_component_ids(bike_id)
    _check_parent_on_bike(bike_id, ids, parents)
    try:
        return component_service.mount_new_component(
            component_type, before_component_id=before_component_id, **parents
        )
    except LookupError as exc:
        raise ValueError("That place no longer exists.") from exc


def move_part(
    bike_id: int,
    component_id: int,
    parents: dict[str, int | None],
    before_component_id: int | None = None,
) -> Component:
    """Mount, move, re-order or unmount a part that is in storage or already on this bike."""
    ids = _bike_component_ids(bike_id)
    component = component_service.get_component(component_id)
    if component is None:
        raise ValueError("That part no longer exists.")
    in_storage = component.parent_bike_id is None and component.parent_component_id is None
    if not (in_storage or component_id in ids):
        raise ValueError("That part is not on this bike.")
    _check_parent_on_bike(bike_id, ids, parents)
    try:
        return component_service.move_component(
            component_id, before_component_id=before_component_id, **parents
        )
    except LookupError as exc:
        raise ValueError("That place no longer exists.") from exc
