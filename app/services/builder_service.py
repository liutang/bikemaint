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
from app.models.component_kinds import BIKE
from app.models.rows import Bike, Component
from app.services import component_service
from app.services.component_service import MoveTarget


@dataclass
class BuilderNode:
    component: Component
    ref: str  # "component:ID", the drop-target reference
    parent_ref: str  # "bike:ID" or "component:ID"
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
class PaletteCategory:
    name: str
    items: list[PaletteItem]


@dataclass
class BuilderView:
    root_ref: str  # "bike:ID" or "component:ID"
    bike: Bike | None  # set when the root is a bike
    component: Component | None  # set when the root is a part
    nodes: list[BuilderNode]
    storage: list[StorageItem]
    palette: list[PaletteCategory]
    crumbs: list[tuple[str, str | None]]

    @property
    def title(self) -> str:
        return (self.bike or self.component).name  # type: ignore[union-attr]


def parse_root(root: str | int) -> tuple[str, int]:
    """`bike:ID` / `component:ID` (a bare int means a bike) -> (kind, id)."""
    if isinstance(root, int):
        return BIKE, root
    kind, _, raw = str(root).partition(":")
    if kind not in (BIKE, "component") or not raw.isdigit():
        raise ValueError("That screen does not exist.")
    return kind, int(raw)


def breadcrumbs(root: str | int) -> list[tuple[str, str | None]]:
    """Garage > bike (or Storage) > ancestors > the current screen (no link on the last)."""
    kind, root_id = parse_root(root)
    with get_connection() as conn:
        if kind == BIKE:
            bike = bikes_db.get_by_id(conn, root_id)
            return [("Garage", "/"), (bike.name if bike else "Bike", None)]
        chain: list[Component] = []
        node = components_db.get_by_id(conn, root_id)
        while node is not None:
            chain.append(node)
            node = (
                components_db.get_by_id(conn, node.parent_component_id)
                if node.parent_component_id is not None
                else None
            )
        chain.reverse()
        if not chain:
            return [("Garage", "/")]
        top = chain[0]
        head: list[tuple[str, str | None]] = [("Garage", "/")]
        if top.parent_bike_id is not None:
            bike = bikes_db.get_by_id(conn, top.parent_bike_id)
            head.append((bike.name if bike else "Bike", f"/bikes/{top.parent_bike_id}"))
        else:
            head.append(("Storage", "/components"))
        trail = [(c.name, f"/components/{c.id}") for c in chain[:-1]]
        return [*head, *trail, (chain[-1].name, None)]


def root_exists(root: str | int) -> bool:
    """Is there a live bike or part behind this root? (False for malformed roots too.)"""
    try:
        kind, root_id = parse_root(root)
    except ValueError:
        return False
    with get_connection() as conn:
        found = (
            bikes_db.get_by_id(conn, root_id)
            if kind == BIKE
            else components_db.get_by_id(conn, root_id)
        )
    return found is not None


def scope_component_ids(root: str | int) -> set[int]:
    """Component ids on the screen: a bike's whole tree, or the part itself plus its sub-parts."""
    kind, root_id = parse_root(root)
    with get_connection() as conn:
        if kind == BIKE:
            return {c.id for c in components_db.get_tree_for_bike(conn, root_id)}
        if components_db.get_by_id(conn, root_id) is None:
            return set()
        return {root_id} | {c.id for c in components_db.get_descendants(conn, root_id)}


def build_view(root: str | int) -> BuilderView | None:
    kind, root_id = parse_root(root)
    root_ref = f"{kind}:{root_id}"
    with get_connection() as conn:
        bike = component = None
        if kind == BIKE:
            bike = bikes_db.get_by_id(conn, root_id)
            if bike is None:
                return None
            tree = components_db.get_tree_for_bike(conn, root_id)
            top = [c for c in tree if c.parent_bike_id == root_id]
        else:
            component = components_db.get_by_id(conn, root_id)
            if component is None:
                return None
            tree = components_db.get_descendants(conn, root_id)
            top = components_db.list_children(conn, parent_component_id=root_id)
        storage = [c for c in components_db.list_in_storage(conn) if c.id != root_id or kind == BIKE]

    children_of: dict[int | None, list[Component]] = {}
    for c in tree:
        children_of.setdefault(c.parent_component_id, []).append(c)

    def _nodes(siblings: list[Component], parent_ref: str) -> list[BuilderNode]:
        nodes = []
        for index, c in enumerate(siblings):
            kids = children_of.get(c.id, [])
            nodes.append(
                BuilderNode(
                    component=c,
                    ref=f"component:{c.id}",
                    parent_ref=parent_ref,
                    targets=component_service.list_move_targets(c.id, root=root_ref),
                    can_up=index > 0,
                    up_before=siblings[index - 1].id if index > 0 else None,
                    can_down=index < len(siblings) - 1,
                    down_before=siblings[index + 2].id if index + 2 < len(siblings) else None,
                    children=_nodes(kids, f"component:{c.id}"),
                )
            )
        return nodes

    # Every offered kind, grouped by category; any part can go in any place (specs/020).
    places = component_service.list_placement_targets(root=root_ref)
    palette = [
        PaletteCategory(
            category, [PaletteItem(k.type, k.name, list(places)) for k in kinds]
        )
        for category, kinds in component_kinds.offered_by_category()
    ]

    return BuilderView(
        root_ref=root_ref,
        bike=bike,
        component=component,
        nodes=_nodes(top, root_ref),
        storage=[
            StorageItem(c, component_service.list_move_targets(c.id, root=root_ref)) for c in storage
        ],
        palette=palette,
        crumbs=breadcrumbs(root_ref),
    )


def _check_parent_in_scope(root: str, ids: set[int], parents: dict[str, int | None]) -> None:
    kind, root_id = parse_root(root)
    bike_ok = kind == BIKE and parents["parent_bike_id"] == root_id
    component_ok = parents["parent_component_id"] in ids
    is_storage = parents["parent_bike_id"] is None and parents["parent_component_id"] is None
    if not (bike_ok or component_ok or is_storage):
        raise ValueError("That place is not on this screen.")


def add_part(
    root: str,
    component_type: str,
    parents: dict[str, int | None],
    before_component_id: int | None = None,
    installed_at: str | None = None,
) -> Component:
    """Create a new part from the palette inside this screen's scope, or in storage.

    `installed_at` (default now) is when it went on the parent; it is ignored for storage.
    """
    ids = scope_component_ids(root)
    _check_parent_in_scope(root, ids, parents)  # storage (no parent) is always allowed
    try:
        return component_service.mount_new_component(
            component_type,
            before_component_id=before_component_id,
            installed_at=installed_at if any(parents.values()) else None,
            **parents,
        )
    except LookupError as exc:
        raise ValueError("That place no longer exists.") from exc


def move_part(
    root: str,
    component_id: int,
    parents: dict[str, int | None],
    before_component_id: int | None = None,
) -> Component:
    """Mount, move, re-order or unmount a part that is in storage or inside this screen's scope."""
    ids = scope_component_ids(root)
    component = component_service.get_component(component_id)
    if component is None:
        raise ValueError("That part no longer exists.")
    in_storage = component.parent_bike_id is None and component.parent_component_id is None
    if not (in_storage or component_id in ids):
        raise ValueError("That part is not on this screen.")
    _check_parent_in_scope(root, ids, parents)
    try:
        return component_service.move_component(
            component_id, before_component_id=before_component_id, **parents
        )
    except LookupError as exc:
        raise ValueError("That place no longer exists.") from exc


def delete_part(root: str, component_id: int, *, confirmed: bool = False) -> None:
    """Delete a part (and its sub-parts) that is inside this screen's scope.

    Raises `component_service.ConfirmationRequiredError` when sub-parts, maintenance history or a
    schedule need an explicit yes first.
    """
    ids = scope_component_ids(root)
    if component_id not in ids:
        raise ValueError("That part is not on this screen.")
    try:
        component_service.delete_component(component_id, confirmed=confirmed)
    except LookupError as exc:
        raise ValueError("That part no longer exists.") from exc
