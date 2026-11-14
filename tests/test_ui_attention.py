"""The "What needs attention" page (specs/003-cockpit-theme, User Story 2)."""

import re
from datetime import date, timedelta

import pytest

from app.services import bike_service, schedule_service

TODAY = date.today()


def _bike(name="Gravel Bike"):
    return bike_service.create_bike(name=name)


def _overdue(bike, name, days_late):
    schedule_service.create_schedule(
        bike_id=bike.id, name=name, interval_days=10, today=TODAY - timedelta(days=10 + days_late)
    )


def _due_soon(bike, name, days_left):
    schedule_service.create_schedule(
        bike_id=bike.id, name=name, interval_days=days_left, today=TODAY
    )


def _card(html, schedule_id):
    match = re.search(
        rf'<article class="attention-card[^"]*" id="schedule-row-{schedule_id}">.*?</article>', html, re.S
    )
    assert match, f"card {schedule_id} not found"
    return match.group(0)


def _cards(html):
    return re.findall(r'<article class="attention-card', html)


def test_page_is_titled_what_needs_attention(signed_in_client):
    _overdue(_bike(), "Brake check", 5)

    html = signed_in_client.get("/maintenance/due").text

    assert re.search(r"<h1[^>]*>\s*What needs attention\s*</h1>", html)
    assert 'id="attention"' in html


def test_overdue_card_has_a_full_red_ring_labelled_in_days(signed_in_client):
    _overdue(_bike(), "Brake check", 30)

    card = _card(signed_in_client.get("/maintenance/due").text, 1)

    assert 'class="attention-card status-overdue"' in card
    assert re.search(r'<svg class="ring"[^>]*role="img"[^>]*aria-label="Overdue by 30 days"', card)
    assert re.search(r'class="ring-value">30d<', card)
    assert re.search(r'class="ring-caption">late<', card)
    assert 'stroke-dashoffset="0' in card  # fully filled
    assert "Brake check" in card and "Gravel Bike" in card
    assert "Mark done" in card
    assert "badge-overdue" in card  # text + icon status, not color alone


def test_due_soon_card_has_a_partial_arc_labelled_days_left(signed_in_client):
    _due_soon(_bike(), "Replace chain", 4)

    card = _card(signed_in_client.get("/maintenance/due").text, 1)

    assert 'status-soon' in card
    assert re.search(r'aria-label="Due in 4 days"', card)
    assert re.search(r'class="ring-value">4d<', card)
    assert re.search(r'class="ring-caption">left<', card)
    offset = float(re.search(r'class="ring-progress"[^>]*stroke-dashoffset="([\d.]+)"', card).group(1))
    assert 0 < offset < 251  # partial arc


def test_due_today_never_says_zero_days_or_late(signed_in_client):
    _due_soon(_bike(), "Tire swap", 0)

    card = _card(signed_in_client.get("/maintenance/due").text, 1)

    assert "Due today" in card
    assert "0d" not in card and "late" not in card.lower().replace("ring-caption", "")


def _usage_overdue_card(client, **schedule):
    bike = bike_service.create_bike(name="Mileage Bike", manual_baseline_mileage=0)
    schedule_service.create_schedule(bike_id=bike.id, name="Chain", **schedule)
    from app.db import connection

    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET total_mileage = 500")
    return _card(client.get("/maintenance/due").text, 1)


def test_overdue_by_mileage_shows_how_many_miles_over(signed_in_client):
    card = _usage_overdue_card(signed_in_client, interval_miles=186)  # 500 ridden, due at 186

    assert 'aria-label="Overdue by 314 miles"' in card
    assert 'class="ring-value">314mi<' in card and 'class="ring-caption">late<' in card


def test_one_mile_over_is_singular(signed_in_client):
    card = _usage_overdue_card(signed_in_client, interval_miles=499)

    assert 'aria-label="Overdue by 1 mile"' in card


def test_a_date_overdue_still_shows_days(signed_in_client):
    bike = _bike()
    _overdue(bike, "Chain", 5)

    card = _card(signed_in_client.get("/maintenance/due").text, 1)

    assert 'aria-label="Overdue by 5 days"' in card


def test_edit_has_a_visible_border_on_the_cards_and_the_other_rows(signed_in_client):
    bike = _bike()
    _overdue(bike, "Chain", 5)

    html = signed_in_client.get("/maintenance/due").text

    assert 'class="btn" href="/schedules/1/edit"' in html
    assert "btn-quiet" not in _card(html, 1)


def test_urgent_cards_are_ordered_most_overdue_first(signed_in_client):
    bike = _bike()
    _due_soon(bike, "Soon", 2)  # id 1
    _overdue(bike, "Slightly late", 2)  # id 2
    _overdue(bike, "Very late", 20)  # id 3

    html = signed_in_client.get("/maintenance/due").text

    order = re.findall(r'<article class="attention-card[^"]*" id="schedule-row-(\d)"', html)
    assert order == ["3", "2", "1"]


def test_columns_are_two_for_a_few_and_three_for_many(signed_in_client):
    bike = _bike()
    for i in range(2):
        _overdue(bike, f"Job {i}", 3)
    assert 'attention-grid cols-2' in signed_in_client.get("/maintenance/due").text
    for i in range(2, 5):
        _overdue(bike, f"Job {i}", 3)
    assert 'attention-grid cols-3' in signed_in_client.get("/maintenance/due").text


def test_six_urgent_tasks_show_six_cards_and_no_more_tile(signed_in_client):
    bike = _bike()
    for i in range(6):
        _overdue(bike, f"Job {i}", 3 + i)

    html = signed_in_client.get("/maintenance/due").text

    assert len(_cards(html)) == 6
    assert "attention-more" not in html


def test_seven_urgent_tasks_collapse_extras_into_a_more_tile(signed_in_client):
    bike = _bike()
    for i in range(7):
        _overdue(bike, f"Job {i}", 3 + i)

    html = signed_in_client.get("/maintenance/due").text

    assert len(_cards(html)) == 5
    more = re.search(r'<a class="attention-more" href="/maintenance/due\?all=1">(.*?)</a>', html, re.S)
    assert more and "+2 more tasks" in more.group(1) and "View all" in more.group(1)


def test_view_all_shows_every_urgent_task(signed_in_client):
    bike = _bike()
    for i in range(8):
        _overdue(bike, f"Job {i}", 3 + i)

    html = signed_in_client.get("/maintenance/due?all=1").text

    assert len(_cards(html)) == 8
    assert "attention-more" not in html
    assert 'href="/maintenance/due"' in html and "Show fewer" in html


def test_all_flag_is_validated_at_the_boundary(signed_in_client):
    bike = _bike()
    for i in range(7):
        _overdue(bike, f"Job {i}", 3 + i)

    for value in ("0", "yes", "<script>", ""):
        html = signed_in_client.get("/maintenance/due", params={"all": value}).text
        assert len(_cards(html)) == 5, value
        assert "<script>" not in html


def test_non_urgent_tasks_are_in_a_compact_list_with_badges(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=200, today=TODAY)  # 1
    schedule_service.create_schedule(bike_id=bike.id, name="Tire swap", interval_miles=800)  # 2

    html = signed_in_client.get("/maintenance/due").text

    assert _cards(html) == []
    items = re.findall(r'<li class="other-row" id="schedule-row-(\d)">(.*?)</li>', html, re.S)
    assert [i for i, _ in items] == ["1", "2"]
    assert "badge-ok" in items[0][1] and "On track" in items[0][1]
    assert "badge-low" in items[1][1] and "No estimate yet" in items[1][1]
    assert all("Mark done" in body for _, body in items)


def test_all_clear_message_when_nothing_is_urgent(signed_in_client):
    schedule_service.create_schedule(bike_id=_bike().id, name="Annual service", interval_days=200, today=TODAY)

    html = signed_in_client.get("/maintenance/due").text

    assert 'class="all-clear"' in html and "Nothing needs attention" in html


def test_empty_state_when_there_are_no_schedules(signed_in_client):
    html = signed_in_client.get("/maintenance/due").text

    assert 'class="empty-state"' in html and "all-clear" not in html


def test_mark_done_with_htmx_returns_the_whole_board_in_place(signed_in_client):
    bike = _bike()
    _overdue(bike, "Brake check", 20)  # id 1
    _overdue(bike, "Chain", 5)  # id 2

    response = signed_in_client.post(
        "/schedules/1/complete", data={"all": "1"}, headers={"hx-request": "true"}
    )

    html = response.text
    assert html.lstrip().startswith('<section id="attention"')
    assert "<html" not in html
    # the completed task moved out of the urgent cards into the compact list; the other stays
    assert [c for c in re.findall(r'<article class="attention-card[^"]*" id="schedule-row-(\d)"', html)] == ["2"]
    assert re.search(r'<li class="other-row[^"]*" id="schedule-row-1">', html)


def test_card_form_targets_the_board_and_keeps_the_view_all_flag(signed_in_client):
    bike = _bike()
    for i in range(7):
        _overdue(bike, f"Job {i}", 3 + i)

    html = signed_in_client.get("/maintenance/due?all=1").text

    card = _card(html, 1)
    assert 'hx-post="/schedules/1/complete"' in card
    assert 'hx-target="#attention"' in card and 'hx-swap="outerHTML"' in card
    assert 'name="all" value="1"' in card
    assert 'action="/schedules/1/complete"' in card  # works without HTMX too


def test_mark_done_without_htmx_still_redirects(signed_in_client):
    _overdue(_bike(), "Brake check", 5)

    response = signed_in_client.post("/schedules/1/complete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/maintenance/due?done=1"


# ------------------------------------------------ owner shows its bike (specs/006, M1)


def test_a_part_schedule_reads_bike_then_part_on_cards_and_in_the_list(signed_in_client):
    from app.services import component_service

    bike = _bike("Gravel Bike")
    chain = component_service.create_component(name="Chain 1", component_type="chain", parent_bike_id=bike.id)
    schedule_service.create_schedule(component_id=chain.id, name="Re-wax", interval_days=3, today=TODAY)  # urgent
    schedule_service.create_schedule(component_id=chain.id, name="Replace", interval_days=300, today=TODAY)  # list

    html = signed_in_client.get("/maintenance/due").text

    card = _card(html, 1)
    assert re.search(r'<span class="owner-bike">Gravel Bike</span>\s*<a href="/components/\d+">Chain 1</a>', card)
    row = re.search(r'<li class="other-row" id="schedule-row-2">.*?</li>', html, re.S).group(0)
    assert re.search(r'<span class="owner-bike">Gravel Bike</span>\s*<a href="/components/\d+">Chain 1</a>', row)


def test_a_bike_level_schedule_shows_just_the_bike(signed_in_client):
    bike = _bike("Gravel Bike")
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=3, today=TODAY)

    card = _card(signed_in_client.get("/maintenance/due").text, 1)

    assert "owner-bike" not in card and ">Gravel Bike</a>" in card


# ------------------------------------------------ Mark done feedback (specs/006, M2)


def _done(client, schedule_id, **extra):
    return client.post(f"/schedules/{schedule_id}/complete", data=extra, headers={"hx-request": "true"})


def test_mark_done_shows_what_happened_and_when_it_is_next_due(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14, today=TODAY)

    html = _done(signed_in_client, 1).text

    message = re.search(r'<p id="board-notice"[^>]*>(.*?)</p>', html, re.S).group(1)
    assert "Marked done: Check tire pressure" in message and "Next due" in message
    assert re.search(r"\d{4}-\d\d-\d\d", message)
    assert 'role="status"' in html


def test_the_completed_task_is_highlighted_in_its_new_place(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=200, today=TODAY)  # 1
    schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14, today=TODAY)  # 2

    html = _done(signed_in_client, 1).text

    done_row = re.search(r'<li class="other-row[^"]*" id="schedule-row-1">', html).group(0)
    assert "is-just-done" in done_row
    assert "is-just-done" not in re.search(r'<li class="other-row[^"]*" id="schedule-row-2">', html).group(0)


def test_an_urgent_task_that_is_done_moves_down_and_shows_its_new_date(signed_in_client):
    bike = _bike()
    _overdue(bike, "Brake check", 20)  # id 1

    html = _done(signed_in_client, 1).text

    assert _cards(html) == []  # no longer urgent
    row = re.search(r'<li class="other-row[^"]*" id="schedule-row-1">.*?</li>', html, re.S).group(0)
    assert "is-just-done" in row and re.search(r"Due \d{4}-\d\d-\d\d", row)


def test_mark_done_buttons_are_disabled_while_the_request_runs(signed_in_client):
    bike = _bike()
    _overdue(bike, "Brake check", 5)
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=200, today=TODAY)

    html = signed_in_client.get("/maintenance/due").text

    forms = re.findall(r'<form[^>]*action="/schedules/\d+/complete"[^>]*>', html)
    assert len(forms) == 2 and all('hx-disabled-elt="find button"' in f for f in forms)


def test_rapid_repeat_clicks_log_one_entry_and_still_show_feedback(signed_in_client):
    from app.services import maintenance_service

    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14, today=TODAY)

    for _ in range(4):
        response = _done(signed_in_client, 1)

    logged = [e for e in maintenance_service.list_for_bike(bike.id) if e.schedule_id == 1]
    assert len(logged) == 1
    assert "Marked done: Check tire pressure" in response.text


def test_the_non_htmx_redirect_shows_the_same_confirmation_on_the_page(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14, today=TODAY)

    redirect = signed_in_client.post("/schedules/1/complete", follow_redirects=False)
    page = signed_in_client.get(redirect.headers["location"]).text

    assert redirect.status_code == 303 and redirect.headers["location"] == "/maintenance/due?done=1"
    assert "Marked done: Check tire pressure" in page and "is-just-done" in page


@pytest.mark.parametrize("value", ["x", "-1", "999", "1; drop", ""])
def test_a_bad_done_parameter_is_ignored(signed_in_client, value):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Check tire pressure", interval_days=14, today=TODAY)

    page = signed_in_client.get("/maintenance/due", params={"done": value})

    assert page.status_code == 200 and "Marked done" not in page.text


def test_the_notice_region_is_always_present_for_screen_readers(signed_in_client):
    bike = _bike()
    schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=200, today=TODAY)

    html = signed_in_client.get("/maintenance/due").text

    assert re.search(r'<p id="board-notice" class="board-notice"[^>]*role="status"[^>]*aria-live="polite"', html)
