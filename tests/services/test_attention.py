"""Ring math and the urgent/other split behind "What needs attention" (specs/003-cockpit-theme)."""

from datetime import date, timedelta

import pytest

from app.models.rows import MaintenanceSchedule
from app.services.schedule_service import (
    DueItem,
    Projection,
    ring_fraction,
    split_attention,
)

TODAY = date(2026, 6, 15)


def _item(schedule_id, status, days_until, *, owner="Bike"):
    due_at = None if days_until is None else TODAY + timedelta(days=days_until)
    projection = Projection(
        due_at=due_at,
        remaining_miles=None,
        is_low_confidence=status == "no_estimate",
        is_overdue=status == "overdue",
    )
    schedule = MaintenanceSchedule(
        id=schedule_id, bike_id=1, component_id=None, name=f"Task {schedule_id}",
        interval_miles=None, interval_days=30, baseline_mileage=0.0, baseline_date="2026-01-01",
        cycle_number=1, is_active=True, created_at="", updated_at="",
    )
    return DueItem(
        schedule=schedule, owner_type="bike", owner_id=1, owner_name=owner,
        projection=projection, status=status, days_until=days_until,
    )


def test_overdue_ring_is_always_full():
    assert ring_fraction("overdue", -30, 7) == 1.0
    assert ring_fraction("overdue", None, 7) == 1.0


def test_due_soon_ring_grows_as_the_date_nears():
    far = ring_fraction("due_soon", 6, 7)
    near = ring_fraction("due_soon", 1, 7)
    today = ring_fraction("due_soon", 0, 7)
    assert far < near < today == 1.0


def test_due_soon_ring_never_disappears_and_never_exceeds_full():
    assert ring_fraction("due_soon", 7, 7) == pytest.approx(0.08)
    assert ring_fraction("due_soon", 50, 7) == pytest.approx(0.08)
    assert ring_fraction("due_soon", -1, 7) == 1.0
    assert ring_fraction("due_soon", 3, 0) == 1.0  # zero lead time: nothing to divide by


def test_non_urgent_statuses_have_no_ring():
    assert ring_fraction("on_track", 90, 7) == 0.0
    assert ring_fraction("no_estimate", None, 7) == 0.0


def test_urgent_items_are_ordered_overdue_first_then_soonest_first():
    items = [
        _item(1, "due_soon", 5),
        _item(2, "overdue", -3),
        _item(3, "due_soon", 1),
        _item(4, "overdue", -30),
        _item(5, "on_track", 90),
    ]

    board = split_attention(items)

    assert [i.schedule.id for i in board.shown] == [4, 2, 3, 1]
    assert [i.schedule.id for i in board.others] == [5]
    assert board.overflow_count == 0


def test_overdue_by_mileage_without_a_date_sorts_among_the_overdue():
    items = [_item(1, "overdue", None), _item(2, "overdue", -10), _item(3, "due_soon", 2)]

    board = split_attention(items)

    assert [i.schedule.id for i in board.shown] == [2, 1, 3]


def test_non_urgent_items_never_become_cards():
    items = [_item(1, "no_estimate", None), _item(2, "on_track", 40)]

    board = split_attention(items)

    assert board.shown == [] and board.urgent_total == 0
    assert [i.schedule.id for i in board.others] == [2, 1]  # dated first, then no-estimate


def test_exactly_six_urgent_tasks_show_six_cards_and_no_overflow():
    items = [_item(i, "overdue", -i) for i in range(1, 7)]

    board = split_attention(items)

    assert len(board.shown) == 6 and board.overflow_count == 0 and board.urgent_total == 6


def test_seven_urgent_tasks_show_five_cards_and_a_two_more_tile():
    items = [_item(i, "overdue", -i) for i in range(1, 8)]

    board = split_attention(items)

    assert len(board.shown) == 5
    assert board.overflow_count == 2
    assert board.urgent_total == 7
    assert [i.schedule.id for i in board.shown] == [7, 6, 5, 4, 3]  # most overdue first


def test_show_all_reveals_every_urgent_task():
    items = [_item(i, "overdue", -i) for i in range(1, 10)]

    board = split_attention(items, show_all=True)

    assert len(board.shown) == 9 and board.overflow_count == 0
