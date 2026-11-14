from datetime import date

import httpx
import pytest
import respx

from app.db import accounts, connection
from app.db import notifications as notifications_db
from app.services import bike_service, notification_service, schedule_service

TODAY = date.today()
WEBHOOK_URL = "https://discord.example/api/webhooks/123/abc"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    connection.run_migrations()
    monkeypatch.setattr(notification_service, "_sleep", lambda seconds: None)
    return path


def _account(webhook_url=None, lead_time_days=7):
    with connection.get_connection() as conn:
        account = accounts.upsert_from_strava(
            conn,
            strava_athlete_id=1,
            access_token="a",
            refresh_token="r",
            expires_at="2099-01-01T00:00:00.000000Z",
        )
        conn.execute(
            "UPDATE account SET notification_webhook_url = ?, notification_lead_time_days = ? "
            "WHERE id = ?",
            (webhook_url, lead_time_days, account.id),
        )
    return account


def _due_soon_schedule(days=3):
    bike = bike_service.create_bike(name="Gravel Bike")
    return schedule_service.create_schedule(
        bike_id=bike.id, name="Replace chain", interval_days=days, today=TODAY
    )


def _notification_count():
    with connection.get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM notification").fetchone()["n"]


def test_two_checks_in_the_same_cycle_create_exactly_one_notification(db_path):
    _account()
    schedule = _due_soon_schedule()

    first = notification_service.check_due_schedules(today=TODAY)
    second = notification_service.check_due_schedules(today=TODAY)

    assert [n.schedule_id for n in first] == [schedule.id]
    assert second == []
    assert _notification_count() == 1


def test_completing_the_schedule_allows_a_notification_for_the_next_cycle(db_path):
    _account()
    schedule = _due_soon_schedule()
    notification_service.check_due_schedules(today=TODAY)

    schedule_service.complete_schedule(schedule.id, today=TODAY)
    # Next cycle's due date is `interval_days` after completion — move "today" into its window.
    later = date.fromordinal(TODAY.toordinal() + 1)
    created = notification_service.check_due_schedules(today=later)

    assert [n.cycle_number for n in created] == [2]
    assert _notification_count() == 2


def test_schedule_outside_the_lead_time_window_is_not_notified(db_path):
    _account(lead_time_days=7)
    _due_soon_schedule(days=30)

    assert notification_service.check_due_schedules(today=TODAY) == []


def test_overdue_schedule_is_notified(db_path):
    _account(lead_time_days=7)
    _due_soon_schedule(days=3)
    in_the_future = date.fromordinal(TODAY.toordinal() + 20)

    assert len(notification_service.check_due_schedules(today=in_the_future)) == 1


def test_schedule_without_a_projected_date_is_not_notified(db_path):
    _account()
    bike = bike_service.create_bike(name="New Bike")
    schedule_service.create_schedule(bike_id=bike.id, name="Mileage only", interval_miles=500)

    assert notification_service.check_due_schedules(today=TODAY) == []


def test_no_account_means_no_notifications(db_path):
    _due_soon_schedule()

    assert notification_service.check_due_schedules(today=TODAY) == []


@respx.mock
def test_webhook_payload_follows_the_contract(db_path):
    _account(webhook_url=WEBHOOK_URL)
    schedule = _due_soon_schedule(days=3)
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(204))

    notification_service.check_due_schedules(today=TODAY)

    assert route.call_count == 1
    body = route.calls[0].request.content
    import json

    payload = json.loads(body)
    assert "Replace chain" in payload["content"]
    assert "Gravel Bike" in payload["content"]
    assert payload["schedule"]["id"] == schedule.id
    assert payload["schedule"]["name"] == "Replace chain"
    assert payload["schedule"]["cycle_number"] == 1
    assert payload["schedule"]["owner_type"] == "bike"
    assert payload["schedule"]["owner_name"] == "Gravel Bike"
    assert payload["schedule"]["projected_due_at"] == date.fromordinal(TODAY.toordinal() + 3).isoformat()
    assert payload["schedule"]["projected_remaining_miles"] is None
    assert payload["schedule"]["is_low_confidence"] is False
    with connection.get_connection() as conn:
        stored = notifications_db.list_unacknowledged(conn)[0]
    assert stored.webhook_delivered is True
    assert stored.webhook_delivery_error is None


@respx.mock
def test_webhook_is_retried_up_to_twice_then_succeeds(db_path):
    route = respx.post(WEBHOOK_URL).mock(
        side_effect=[httpx.Response(500), httpx.Response(502), httpx.Response(200)]
    )

    delivered, error = notification_service.deliver_webhook(WEBHOOK_URL, {"content": "hi"})

    assert (delivered, error) == (True, None)
    assert route.call_count == 3


@respx.mock
def test_webhook_failure_after_retries_reports_an_error(db_path):
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))

    delivered, error = notification_service.deliver_webhook(WEBHOOK_URL, {"content": "hi"})

    assert delivered is False
    assert "500" in error
    assert route.call_count == 3


@respx.mock
def test_webhook_network_error_is_reported_not_raised(db_path):
    respx.post(WEBHOOK_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

    delivered, error = notification_service.deliver_webhook(WEBHOOK_URL, {"content": "hi"})

    assert delivered is False
    assert error


@respx.mock
def test_failed_webhook_never_blocks_the_in_app_notification(db_path):
    _account(webhook_url=WEBHOOK_URL)
    _due_soon_schedule()
    respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(500))

    created = notification_service.check_due_schedules(today=TODAY)

    assert len(created) == 1
    with connection.get_connection() as conn:
        stored = notifications_db.list_unacknowledged(conn)[0]
    assert stored.webhook_delivered is False
    assert "500" in stored.webhook_delivery_error


def test_acknowledge_removes_notification_from_the_unacknowledged_list(db_path):
    _account()
    _due_soon_schedule()
    created = notification_service.check_due_schedules(today=TODAY)

    notification_service.acknowledge(created[0].id)

    assert notification_service.list_unacknowledged() == []


@respx.mock
def test_a_schedule_with_notifications_off_sends_nothing_but_stays_on_the_board(db_path):
    # 040 FR-007
    _account(webhook_url=WEBHOOK_URL)
    bike = bike_service.create_bike(name="Gravel Bike")
    quiet = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="period", interval_value=1,
        interval_unit="weeks", notify=False, today=TODAY - __import__("datetime").timedelta(days=5),
    )
    route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(204))

    created = notification_service.check_due_schedules(today=TODAY)

    assert created == [] and route.call_count == 0 and _notification_count() == 0
    assert [i.schedule.id for i in schedule_service.list_due_overview(today=TODAY)] == [quiet.id]


def test_the_webhook_text_and_payload_name_the_unit_left(db_path):
    bike = bike_service.create_bike(name="Gravel Bike")
    schedule = schedule_service.create_schedule(
        bike_id=bike.id, service_type="Check", interval_kind="usage", interval_value=3,
        interval_unit="rides", today=TODAY,
    )
    item = schedule_service.get_due_item(schedule.id, today=TODAY)
    # pretend the usage is almost up: 2 rides left, due soon
    from dataclasses import replace
    item = replace(item, projection=replace(item.projection, remaining=2.0, remaining_unit="rides", remaining_miles=None))

    payload = notification_service.build_webhook_payload(item)

    assert "2 rides remaining" in payload["content"] and "mi remaining" not in payload["content"]
    assert payload["schedule"]["projected_remaining"] == 2.0
    assert payload["schedule"]["projected_remaining_unit"] == "rides"
    assert payload["schedule"]["projected_remaining_miles"] is None


def test_a_miles_schedule_keeps_the_miles_wording_and_field(db_path):
    bike = bike_service.create_bike(name="Gravel Bike")
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Chain", interval_miles=100, today=TODAY)
    item = schedule_service.get_due_item(schedule.id, today=TODAY)

    payload = notification_service.build_webhook_payload(item)

    assert "100 mi remaining" in payload["content"]
    assert payload["schedule"]["projected_remaining_miles"] == 100.0
    assert payload["schedule"]["projected_remaining_unit"] == "miles"
