import re
import pytest

from app.services import bike_service


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/bikes/1/maintenance"),
        ("get", "/bikes/1/maintenance/new"),
        ("post", "/bikes/1/maintenance"),
        ("get", "/components/1/maintenance"),
        ("get", "/components/1/maintenance/new"),
        ("post", "/components/1/maintenance"),
        ("get", "/maintenance/1/edit"),
        ("post", "/maintenance/1"),
        ("post", "/maintenance/1/delete"),
    ],
)
def test_maintenance_routes_redirect_unauthenticated_requests_to_login(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _login(client, monkeypatch, athlete_id=42):
    from app.services import bike_service, strava_client

    monkeypatch.setattr(
        strava_client,
        "exchange_code_for_token",
        lambda code: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_at": 1893456000,
            "athlete": {"id": athlete_id},
        },
    )
    client.get("/auth/strava/callback?code=auth-code", follow_redirects=False)


def test_log_then_view_bike_maintenance_history(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=50)

    response = client.post(
        "/bikes/1/maintenance",
        data={"service_type": "Replace", "performed_at": "2026-05-01"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/bikes/1/maintenance"

    history = client.get("/bikes/1/maintenance")
    assert history.status_code == 200
    assert "Replace" in history.text
    assert "2026-05-01" in history.text


def test_invalid_maintenance_entry_returns_422(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)

    response = client.post(
        "/bikes/1/maintenance", data={"service_type": "", "performed_at": "not-a-date"}
    )

    assert response.status_code == 422


def test_edit_and_delete_maintenance_entry(client, monkeypatch):
    _login(client, monkeypatch)
    bike_service.create_bike(name="Road Bike", manual_baseline_mileage=0)
    client.post(
        "/bikes/1/maintenance", data={"service_type": "Clean", "performed_at": "2026-05-01"}
    )

    edit = client.post(
        "/maintenance/1",
        data={
            "service_type": "Check",
            "performed_at": "2026-05-02",
            "mileage_at_service": "10",
        },
        follow_redirects=False,
    )
    assert edit.status_code == 303
    assert "Check" in client.get("/bikes/1/maintenance").text

    deleted = client.post("/maintenance/1/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert "New" not in client.get("/bikes/1/maintenance").text


def test_component_maintenance_history_route(client, monkeypatch):
    _login(client, monkeypatch)
    client.post("/components", data={"name": "Chain", "component_type": "chain"})

    client.post(
        "/components/1/maintenance",
        data={"service_type": "Lube/Wax", "performed_at": "2026-05-01"},
    )

    response = client.get("/components/1/maintenance")
    assert response.status_code == 200
    assert "Lube/Wax" in response.text


def test_maintenance_for_unknown_bike_returns_404(client, monkeypatch):
    _login(client, monkeypatch)

    assert client.get("/bikes/999/maintenance").status_code == 404


# ------------------------------------------------ date and time in the history (specs/006, M2)

import re  # noqa: E402

from app.services import component_service, maintenance_service  # noqa: E402


def _rows(html):
    return re.findall(r"<tr[^>]*>.*?</tr>", html.split("<tbody>")[1], re.S)


def test_the_form_has_an_optional_time_field(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance/new").text

    assert re.search(r'<input id="performed_time" name="performed_time" type="time"', html)
    assert not re.search(r'<input id="performed_time"[^>]*required', html)


def test_a_typed_time_is_saved_and_shown_with_the_date(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")

    signed_in_client.post(
        f"/bikes/{bike.id}/maintenance",
        data={"service_type": "Lube/Wax", "performed_at": "2026-05-01", "performed_time": "14:30"},
    )

    (entry,) = maintenance_service.list_for_bike(bike.id)
    assert entry.performed_time == "14:30"
    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text
    assert "Date &amp; time" in html and "2026-05-01 14:30" in html


def test_without_a_time_a_manual_entry_shows_just_the_date(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    signed_in_client.post(f"/bikes/{bike.id}/maintenance", data={"service_type": "Check", "performed_at": "2026-05-01"})

    (entry,) = maintenance_service.list_for_bike(bike.id)
    row = _rows(signed_in_client.get(f"/bikes/{bike.id}/maintenance").text)[0]

    assert entry.performed_time is None
    assert "2026-05-01" in row and "<time" not in row


@pytest.mark.parametrize("bad", ["25:00", "12:60", "noon", "1:5", "12:30:00", "<b>"])
def test_a_malformed_time_is_rejected_beside_the_field(signed_in_client, bad):
    bike = bike_service.create_bike(name="Road Bike")

    response = signed_in_client.post(
        f"/bikes/{bike.id}/maintenance",
        data={"service_type": "Topup", "performed_at": "2026-05-01", "performed_time": bad},
    )

    assert response.status_code == 422 and 'id="performed_time-error"' in response.text
    assert maintenance_service.list_for_bike(bike.id) == []


def test_editing_an_entry_can_change_its_time(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    entry = maintenance_service.log_maintenance(bike_id=bike.id, description="x", performed_at="2026-05-01")

    signed_in_client.post(
        f"/maintenance/{entry.id}",
        data={"service_type": "Topup", "performed_at": "2026-05-01", "performed_time": "09:05"},
    )

    assert maintenance_service.get_entry(entry.id).performed_time == "09:05"
    assert 'value="09:05"' in signed_in_client.get(f"/maintenance/{entry.id}/edit").text


def test_adding_a_part_leaves_no_row_in_the_maintenance_history(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    component_service.create_component(name="Chain 1", component_type="chain", parent_bike_id=bike.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text

    assert "No maintenance logged yet" in html and "<tbody>" not in html
    assert "Added Chain 1" not in html and "entry-event" not in html and "entry-tag" not in html


def test_completed_tasks_show_their_time_too(signed_in_client):
    from app.services import schedule_service

    bike = bike_service.create_bike(name="Road Bike")
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=30)
    schedule_service.complete_schedule(schedule.id)

    row = _rows(signed_in_client.get(f"/bikes/{bike.id}/maintenance").text)[0]

    assert "Annual service" in row and "<time datetime=" in row and "data-local" not in row 


def test_history_shows_only_the_logged_work_in_time_order(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    maintenance_service.log_maintenance(bike_id=bike.id, description="Old job", performed_at="2000-01-01")
    component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    maintenance_service.log_maintenance(bike_id=bike.id, description="New job", performed_at="2026-01-01")

    descriptions = [e.description for e in maintenance_service.list_for_bike(bike.id)]

    assert descriptions == ["New job", "Old job"]  # latest first (specs/044)


def test_history_is_latest_first_by_time_then_recorded_order_for_both_owners(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    chain = component_service.create_component(name="Chain", component_type="chain")
    for owner in ({"bike_id": bike.id}, {"component_id": chain.id}):
        maintenance_service.log_maintenance(**owner, description="Clean", performed_at="2026-05-01", performed_time="09:00")
        maintenance_service.log_maintenance(**owner, description="Check", performed_at="2026-05-01", performed_time="17:30")
        maintenance_service.log_maintenance(**owner, description="Topup", performed_at="2026-04-30", performed_time="23:00")

    for entries in (maintenance_service.list_for_bike(bike.id), maintenance_service.list_for_component(chain.id)):
        assert [e.description for e in entries] == ["Check", "Clean", "Topup"]


def test_the_history_page_no_longer_loads_a_browser_time_script(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")

    assert "localtime.js" not in signed_in_client.get(f"/bikes/{bike.id}/maintenance").text


def test_a_completed_task_shows_in_the_chosen_time_zone(signed_in_client):
    from app.db import accounts, connection
    from app.services import schedule_service, settings_service

    with connection.get_connection() as conn:
        account = accounts.get_singleton(conn)
    settings_service.set_timezone(account.id, "Asia/Kolkata")
    bike = bike_service.create_bike(name="Road Bike")
    schedule = schedule_service.create_schedule(bike_id=bike.id, name="Annual service", interval_days=30)
    schedule_service.complete_schedule(schedule.id)

    row = _rows(signed_in_client.get(f"/bikes/{bike.id}/maintenance").text)[0]

    assert re.search(r"\d{4}-\d\d-\d\d \d{1,2}:\d\d[AP]M IST</time>", row)


def test_logged_maintenance_stays_editable_and_deletable_after_the_install_history_split(signed_in_client):
    bike = bike_service.create_bike(name="Road Bike")
    entry = maintenance_service.log_maintenance(bike_id=bike.id, description="Waxed chain", performed_at="2026-05-01")
    component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)  # logs nothing

    row = _rows(signed_in_client.get(f"/bikes/{bike.id}/maintenance").text)[0]

    assert "Waxed chain" in row
    assert f'href="/maintenance/{entry.id}/edit">Edit</a>' in row
    assert f'action="/maintenance/{entry.id}/delete"' in row
    assert signed_in_client.get(f"/maintenance/{entry.id}/edit").status_code == 200


def test_the_new_form_explains_that_a_blank_mileage_is_worked_out_from_the_rides(signed_in_client):
    # 038 FR-004
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance/new").text

    assert "calculated from the rides up to the date and time performed" in html
    assert "Leave blank to use the current total" not in html


SERVICES = ["Charge", "Check", "Clean", "Lube/Wax", "Replace", "Service", "Topup"]


def test_the_log_form_has_a_service_type_drop_down_and_no_description(signed_in_client):
    # 042 FR-001
    bike = bike_service.create_bike(name="Road")

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance/new").text

    select = re.search(r'<select[^>]*name="service_type"[^>]*>(.*?)</select>', html, re.S).group(1)
    assert [o for o in re.findall(r'<option value="([^"]*)"', select) if o] == SERVICES
    assert 'name="description"' not in html and "Description" not in html
    assert re.search(r'<label for="service_type">Service type</label>', html)


@pytest.mark.parametrize("bad", ["", "Polish", "lube/wax"])
def test_a_missing_or_unlisted_service_type_is_refused_beside_the_field(signed_in_client, bad):
    bike = bike_service.create_bike(name="Road")

    response = signed_in_client.post(
        f"/bikes/{bike.id}/maintenance", data={"service_type": bad, "performed_at": "2026-05-01"}
    )

    assert response.status_code == 422 and 'id="service_type-error"' in response.text
    assert maintenance_service.list_for_bike(bike.id) == []


def test_the_chosen_service_type_is_recorded_and_the_list_column_is_titled_for_it(signed_in_client):
    bike = bike_service.create_bike(name="Road")

    signed_in_client.post(f"/bikes/{bike.id}/maintenance", data={"service_type": "Topup", "performed_at": "2026-05-01"})

    (entry,) = maintenance_service.list_for_bike(bike.id)
    assert entry.description == "Topup"
    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text
    assert '<th scope="col">Service type</th>' in html and "Topup" in html and "Description" not in html


def test_an_older_free_text_entry_shows_unchanged_and_needs_a_type_when_edited(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    old = maintenance_service.log_maintenance(bike_id=bike.id, description="Lubed the chain", performed_at="2026-05-01")
    listed = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text
    assert "Lubed the chain" in listed

    form = signed_in_client.get(f"/maintenance/{old.id}/edit").text

    assert "before service types" in form
    assert not re.search(r'<option value="[A-Z][^"]*" selected>', form.split('name="service_type"')[1].split("</select>")[0])
    refused = signed_in_client.post(f"/maintenance/{old.id}", data={"service_type": "", "performed_at": "2026-05-01"})
    assert refused.status_code == 422
    assert signed_in_client.post(f"/maintenance/{old.id}", data={"service_type": "Lube/Wax", "performed_at": "2026-05-01"},
                                 follow_redirects=False).status_code == 303
    assert maintenance_service.get_entry(old.id).description == "Lube/Wax"


def test_a_typed_entry_opens_for_edit_with_its_type_selected(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    entry = maintenance_service.log_maintenance(bike_id=bike.id, description="Clean", performed_at="2026-05-01")

    form = signed_in_client.get(f"/maintenance/{entry.id}/edit").text

    assert '<option value="Clean" selected>' in form and "before service types" not in form


def _wheel_with_tire(signed_in_client):
    wheel = component_service.create_component(name="Wheel", component_type="wheel")
    tire = component_service.create_component(name="Road tire", component_type="tire", parent_component_id=wheel.id)
    own = maintenance_service.log_maintenance(component_id=wheel.id, description="Check", performed_at="2026-03-01")
    theirs = maintenance_service.log_maintenance(component_id=tire.id, description="Topup", performed_at="2026-05-01")
    return wheel, tire, own, theirs


def test_a_parts_history_has_a_part_column_with_this_part_and_links_to_attached_parts(signed_in_client):
    wheel, tire, own, theirs = _wheel_with_tire(signed_in_client)

    html = signed_in_client.get(f"/components/{wheel.id}/maintenance").text

    heads = re.findall(r'<th scope="col">([^<]*)</th>', html)
    assert heads == ["Date &amp; time", "Part", "Service type", "Mileage at service", "Actions"]
    rows = re.findall(r"<tr>.*?</tr>", html.split("<tbody>")[1], re.S)
    assert len(rows) == 2
    attached, mine = rows  # latest first
    assert f'<a href="/components/{tire.id}/maintenance">Road tire</a>' in attached and "Topup" in attached
    assert "/edit" not in attached and "/delete" not in attached
    assert "This part" in mine and f'href="/maintenance/{own.id}/edit"' in mine and f'action="/maintenance/{own.id}/delete"' in mine


def test_a_bikes_history_includes_all_attached_parts_recursively_latest_first(signed_in_client):
    # 048 FR-004
    bike = bike_service.create_bike(name="Road")
    wheel = component_service.create_component(name="Wheel", component_type="wheel", parent_bike_id=bike.id)
    tire = component_service.create_component(name="Road tire", component_type="tire", parent_component_id=wheel.id)
    spare = component_service.create_component(name="Spare", component_type="tire")
    mine = maintenance_service.log_maintenance(bike_id=bike.id, description="Clean", performed_at="2026-03-01")
    maintenance_service.log_maintenance(component_id=wheel.id, description="Check", performed_at="2026-04-01")
    deep = maintenance_service.log_maintenance(component_id=tire.id, description="Topup", performed_at="2026-05-01")
    maintenance_service.log_maintenance(component_id=spare.id, description="Replace", performed_at="2026-06-01")

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text

    assert re.findall(r'<th scope="col">([^<]*)</th>', html) == ["Date &amp; time", "Part", "Service type", "Mileage at service", "Actions"]
    rows = re.findall(r"<tr>.*?</tr>", html.split("<tbody>")[1], re.S)
    assert [re.search(r'data-label="Service type">([^<]*)', r).group(1) for r in rows] == ["Topup", "Check", "Clean"]
    assert f'<a href="/components/{tire.id}/maintenance">Road tire</a>' in rows[0]
    assert f'<a href="/components/{wheel.id}/maintenance">Wheel</a>' in rows[1]
    assert "/edit" not in rows[0] and "/edit" not in rows[1]
    assert "This bike" in rows[2] and f'href="/maintenance/{mine.id}/edit"' in rows[2]
    assert "Replace" not in html and deep.id


def test_a_bikes_history_leaves_out_parts_taken_off(signed_in_client):
    bike = bike_service.create_bike(name="Road")
    chain = component_service.create_component(name="Chain", component_type="chain", parent_bike_id=bike.id)
    maintenance_service.log_maintenance(component_id=chain.id, description="Lube/Wax", performed_at="2026-05-01")
    component_service.move_component(chain.id)

    html = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text

    assert "Lube/Wax" not in html and "No maintenance logged yet" in html


def test_a_part_with_only_its_own_entries_marks_them_this_part(signed_in_client):
    chain = component_service.create_component(name="Chain", component_type="chain")
    maintenance_service.log_maintenance(component_id=chain.id, description="Lube/Wax", performed_at="2026-05-01")

    html = signed_in_client.get(f"/components/{chain.id}/maintenance").text

    assert "This part" in html
