"""Rendered-page checks for the modern UI (specs/002-modern-ui, User Stories 2-4)."""

import re


def _add_bike(client, name="Road Bike", bike_type="road", baseline="12.5"):
    from app.services import bike_service

    bike_service.create_bike(
        name=name, bike_type=bike_type, manual_baseline_mileage=float(baseline)
    )


def _add_component(client, name, component_type, **parent):
    return client.post(
        "/components", data={"name": name, "component_type": component_type, **parent}
    )


# ---------------------------------------------------------------- User Story 2: garage


def test_garage_shows_bikes_as_cards_with_quick_actions(signed_in_client):
    _add_bike(signed_in_client)

    html = signed_in_client.get("/").text

    card = re.search(r'<article class="card[^"]*"[^>]*>(.*?)</article>', html, re.S)
    assert card, "bike should render as an <article class=card>"
    body = card.group(1)
    assert 'href="/bikes/1"' in body and "Road Bike" in body
    assert "road" in body
    assert "12.5 mi" in body
    assert 'href="/components/new?parent_bike_id=1"' in body and "Add component" in body
    assert 'href="/bikes/1/maintenance"' in body and "Maintenance history" in body
    assert "View" in body


def test_garage_bike_card_uses_the_cockpit_card_layout(signed_in_client):
    _add_bike(signed_in_client)

    html = signed_in_client.get("/").text

    card = re.search(r'<article class="card bike-card" id="bike-1">(.*?)</article>', html, re.S).group(1)
    assert re.search(r'<span class="bike-card-stat"><strong>12.5 mi</strong>', card)
    assert re.search(r'<span class="chip">road</span>', card)
    assert re.search(r'<a class="btn btn-primary" href="/bikes/1">View</a>', card)
    # secondary actions are quiet, so View is the one primary action on the card
    assert card.count("btn-primary") == 1
    assert 'class="btn btn-quiet" href="/components/new?parent_bike_id=1"' in card
    assert 'class="btn btn-quiet" href="/bikes/1/maintenance"' in card


def test_storage_components_use_the_same_card_style_on_garage_and_storage_pages(signed_in_client):
    _add_component(signed_in_client, "Spare Tire", "tire")

    for path in ("/", "/components"):
        html = signed_in_client.get(path).text
        card = re.search(r'<article class="card bike-card is-storage"[^>]*>(.*?)</article>', html, re.S)
        assert card, path
        assert 'href="/components/1"' in card.group(1) and "Spare Tire" in card.group(1)
        assert '<span class="chip">tire</span>' in card.group(1)
        assert 'class="bike-card-stat"' in card.group(1)


def test_garage_lists_storage_under_its_own_heading(signed_in_client):
    _add_component(signed_in_client, "Spare Tire", "tire")

    html = signed_in_client.get("/").text

    assert re.search(r"<h2[^>]*>\s*In storage\s*</h2>", html)
    assert "Spare Tire" in html


def test_empty_garage_and_storage_show_guidance(signed_in_client):
    html = signed_in_client.get("/").text

    assert html.count('class="empty-state"') >= 2
    assert 'href="/bikes/new"' in html
    assert 'href="/components/new"' in html


def test_empty_storage_page_shows_an_empty_state(signed_in_client):
    html = signed_in_client.get("/components").text

    assert 'class="empty-state"' in html


def test_component_tree_uses_collapsible_details_for_branches(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")
    _add_component(signed_in_client, "Road Tire", "tire", parent_component_id="1")
    _add_component(signed_in_client, "Road Valve", "other", parent_component_id="2")

    html = signed_in_client.get("/bikes/1").text

    assert 'class="tree"' in html
    assert html.count("<details open>") == 2  # wheel and tire have children
    assert html.count("<summary") == 2
    assert html.index("Road Wheel") < html.index("Road Tire") < html.index("Road Valve")
    # Interactive content must not nest inside <summary> (axe: nested-interactive).
    assert not re.search(r"<summary[^>]*>(?:(?!</summary>).)*<(?:a|button)\b", html, re.S)
    assert 'href="/components/1"' in html and 'href="/components/2"' in html
    start = html.rfind("<li", 0, html.index("Road Valve"))
    valve_item = html[start : html.index("</li>", start)]
    assert "<details" not in valve_item  # a leaf is a plain item, not a collapsible branch
    for kind in ("wheel", "tire", "other"):
        assert kind in html
    assert "0.0 mi" in html or "0 mi" in html


def test_bike_without_components_shows_an_empty_state(signed_in_client):
    _add_bike(signed_in_client)

    assert 'class="empty-state"' in signed_in_client.get("/bikes/1").text


def test_unconfirmed_delete_without_htmx_returns_a_full_page_confirmation(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    response = signed_in_client.post("/bikes/1/delete", data={})

    html = response.text
    assert response.status_code == 200
    assert "<main" in html and 'aria-label="Primary"' in html
    assert 'class="confirm"' in html
    assert "btn-danger" in html
    assert 'href="/bikes/1"' in html  # cancel link


def test_unconfirmed_delete_with_htmx_returns_only_the_confirmation_fragment(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    html = signed_in_client.post(
        "/bikes/1/delete", data={}, headers={"hx-request": "true"}
    ).text

    assert 'class="confirm"' in html
    assert "<html" not in html
    assert "btn-danger" in html


def test_component_delete_confirmation_follows_the_same_contract(signed_in_client):
    _add_component(signed_in_client, "Road Wheel", "wheel")
    _add_component(signed_in_client, "Road Tire", "tire", parent_component_id="1")

    page = signed_in_client.post("/components/1/delete", data={})
    fragment = signed_in_client.post(
        "/components/1/delete", data={}, headers={"hx-request": "true"}
    )

    assert "<main" in page.text and 'class="confirm"' in page.text
    assert "<html" not in fragment.text and 'class="confirm"' in fragment.text
    assert 'href="/components/1"' in page.text


def test_confirmed_delete_still_deletes(signed_in_client):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Road Wheel", "wheel", parent_bike_id="1")

    signed_in_client.post("/bikes/1/delete", data={"confirmed": "true"})

    assert signed_in_client.get("/bikes/1").status_code == 404


def test_htmx_delete_without_confirmation_needed_redirects_the_whole_page(signed_in_client):
    _add_bike(signed_in_client)

    response = signed_in_client.post(
        "/bikes/1/delete", data={}, headers={"hx-request": "true"}, follow_redirects=False
    )

    assert response.status_code == 200
    assert response.headers["hx-redirect"] == "/"
    assert signed_in_client.get("/bikes/1").status_code == 404


def test_htmx_component_delete_redirects_to_storage_list(signed_in_client):
    _add_component(signed_in_client, "Spare Tire", "tire")

    response = signed_in_client.post(
        "/components/1/delete", data={}, headers={"hx-request": "true"}, follow_redirects=False
    )

    assert response.headers["hx-redirect"] == "/components"


# ------------------------------------------------------------ User Story 3: dashboard

from datetime import date, timedelta  # noqa: E402

from app.services import notification_service, schedule_service  # noqa: E402


def _row(html: str, schedule_id: int) -> str:
    # Urgent tasks render as cards, the rest as compact list rows (specs/003-cockpit-theme).
    match = re.search(
        rf'<(article|li) class="(?:attention-card|other-row)[^"]*" id="schedule-row-{schedule_id}">.*?</\1>',
        html,
        re.S,
    )
    assert match, f"row {schedule_id} not found"
    return match.group(0)


def _seed_schedules():
    from app.services import bike_service

    bike = bike_service.create_bike(name="Dash Bike")
    today = date.today()
    schedule_service.create_schedule(
        bike_id=bike.id, name="Overdue job", interval_days=10, today=today - timedelta(days=30)
    )  # id 1
    schedule_service.create_schedule(
        bike_id=bike.id, name="Soon job", interval_days=3, today=today
    )  # id 2
    schedule_service.create_schedule(
        bike_id=bike.id, name="Far job", interval_days=100, today=today
    )  # id 3
    schedule_service.create_schedule(
        bike_id=bike.id, name="Mileage job", interval_miles=500
    )  # id 4: no ride history -> no estimate, low confidence


def test_dashboard_rows_carry_status_badges_with_text_and_icon(signed_in_client):
    _seed_schedules()

    html = signed_in_client.get("/maintenance/due").text

    expectations = {
        1: ("badge-overdue", "Overdue"),
        2: ("badge-soon", "Due soon"),
        3: ("badge-ok", "On track"),
        4: ("badge-low", "No estimate yet"),
    }
    for schedule_id, (css, text) in expectations.items():
        row = _row(html, schedule_id)
        badge = re.search(rf'<span class="badge {css}">(.*?)</span>', row, re.S)
        assert badge, f"row {schedule_id} lacks {css}"
        assert text in badge.group(1)
        assert '<svg class="icon" viewBox' in badge.group(1) and 'aria-hidden="true"' in badge.group(1)
    assert "Low confidence" in _row(html, 4)
    assert "Low confidence" not in _row(html, 3)


def test_dashboard_urgent_cards_and_list_are_semantic(signed_in_client):
    _seed_schedules()

    html = signed_in_client.get("/maintenance/due").text

    assert '<section id="attention" aria-labelledby="attention-heading"' in html
    assert 'class="other-list"' in html
    assert html.count('<article class="attention-card') == 2  # overdue + due soon


def test_dashboard_with_no_schedules_shows_an_empty_state(signed_in_client):
    html = signed_in_client.get("/maintenance/due").text

    assert 'class="empty-state"' in html


def _make_alert():
    from app.services import bike_service

    bike = bike_service.create_bike(name="Alert Bike")
    schedule_service.create_schedule(
        bike_id=bike.id, name="Chain swap", interval_days=3, today=date.today()
    )
    return notification_service.check_due_schedules()


def test_due_page_shows_no_alerts_list_even_with_unacknowledged_notifications(signed_in_client):
    _make_alert()

    html = signed_in_client.get("/maintenance/due").text

    assert "Due-soon alerts" not in html
    assert 'class="alert' not in html
    assert "alert-list" not in html


def test_acknowledge_with_htmx_returns_an_empty_fragment(signed_in_client):
    _make_alert()

    response = signed_in_client.post(
        "/notifications/1/acknowledge", headers={"hx-request": "true"}, follow_redirects=False
    )

    assert response.status_code == 200
    assert response.text == ""
    assert notification_service.list_unacknowledged() == []


def test_acknowledge_without_htmx_still_redirects(signed_in_client):
    _make_alert()

    response = signed_in_client.post("/notifications/1/acknowledge", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/maintenance/due"


def test_mark_done_with_htmx_returns_the_updated_board(signed_in_client):
    _seed_schedules()

    response = signed_in_client.post("/schedules/1/complete", headers={"hx-request": "true"})

    html = response.text
    assert html.lstrip().startswith('<section id="attention"')
    assert "<html" not in html
    # Completing the overdue 10-day job restarts its cycle, so it is no longer overdue.
    assert "badge-ok" in _row(html, 1) and "badge-overdue" not in _row(html, 1)


# ------------------------------------------------------------ User Story 4: forms

import pytest  # noqa: E402

BAD_SUBMISSIONS = [
    # (id, path, form data, field with the error, entered value that must be preserved, preserved field)
    ("bike", "/bikes", {"year": "abc", "make": "Trek", "model": "Domane", "category": "road"},
     "year", "Trek", "make"),
    ("bike-edit", "/bikes/1", {"year": "abc", "make": "Trek", "model": "Domane", "category": "road"},
     "year", "Trek", "make"),
    ("component", "/components", {"name": "", "component_type": "chain", "manual_baseline_mileage": "9"},
     "name", "9", "manual_baseline_mileage"),
    ("maintenance", "/bikes/1/maintenance",
     {"description": "", "performed_at": "2026-05-01", "mileage_at_service": "7"},
     "description", "2026-05-01", "performed_at"),
    ("maintenance-date", "/bikes/1/maintenance",
     {"description": "Lube", "performed_at": "not-a-date"}, "performed_at", "Lube", "description"),
    ("schedule", "/bikes/1/schedules", {"name": "", "interval_days": "30"},
     "name", "30", "interval_days"),
    ("mileage", "/bikes/1/mileage/adjust", {"delta_miles": "abc", "reason": "typo"},
     "delta_miles", "typo", "reason"),
    ("webhook", "/settings/webhook", {"notification_webhook_url": "ftp://nope"},
     "notification_webhook_url", "ftp://nope", "notification_webhook_url"),
    ("lead-time", "/settings/notifications", {"notification_lead_time_days": "abc"},
     "notification_lead_time_days", "abc", "notification_lead_time_days"),
]


@pytest.mark.parametrize(
    "path,data,field,kept,kept_field",
    [pytest.param(*row[1:], id=row[0]) for row in BAD_SUBMISSIONS],
)
def test_invalid_form_shows_error_beside_the_field_and_keeps_entries(
    signed_in_client, path, data, field, kept, kept_field
):
    _add_bike(signed_in_client)

    response = signed_in_client.post(path, data=data)
    html = response.text

    assert response.status_code == 422
    assert f'<p class="field-error" id="{field}-error">' in html
    control = re.search(rf'<(?:input|select|textarea)[^>]*\bid="{field}"[^>]*>', html)
    assert control, f"no control with id={field}"
    assert 'aria-invalid="true"' in control.group(0)
    assert f"{field}-error" in control.group(0)  # via aria-describedby
    assert 'role="alert"' in html and 'class="error-summary"' in html
    assert re.search(rf'id="{kept_field}"[^>]*value="{re.escape(kept)}"', html) or re.search(
        rf'value="{re.escape(kept)}"[^>]*id="{kept_field}"', html
    ), f"{kept_field} should keep {kept!r}"


def test_model_level_errors_appear_only_in_the_summary(signed_in_client):
    _add_bike(signed_in_client)

    html = signed_in_client.post("/bikes/1/schedules", data={"name": "No interval"}).text

    # Unchanged message from feature 001, shown in the summary, not tied to one field.
    assert "Set a mileage interval, a time interval, or both." in html
    assert 'class="error-summary"' in html


FORM_PAGES = ["/bikes/new", "/bikes/1/edit", "/components/new", "/components/1/edit",
              "/bikes/1/maintenance/new", "/bikes/1/schedules/new", "/bikes/1/mileage/adjust",
              "/settings"]


@pytest.mark.parametrize("path", FORM_PAGES)
def test_every_control_has_an_associated_label(signed_in_client, path):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Chain", "chain")

    html = signed_in_client.get(path).text

    controls = re.findall(r'<(?:input|select|textarea)\b([^>]*)>', html)
    visible = [c for c in controls if 'type="hidden"' not in c and 'type="submit"' not in c
               and 'type="checkbox"' not in c]
    assert visible, "page should contain form controls"
    for attrs in visible:
        control_id = re.search(r'\bid="([^"]+)"', attrs)
        assert control_id, f"control without id: {attrs}"
        assert f'<label for="{control_id.group(1)}"' in html


@pytest.mark.parametrize("path", FORM_PAGES + ["/components/1"])
def test_each_data_entry_form_has_exactly_one_primary_button(signed_in_client, path):
    _add_bike(signed_in_client)
    _add_component(signed_in_client, "Chain", "chain")

    html = signed_in_client.get(path).text

    for form in re.findall(r"<form\b.*?</form>", html, re.S):
        has_entry = re.search(r'<(?:input|select|textarea)\b(?![^>]*type="hidden")', form)
        if has_entry and 'action="/logout"' not in form:
            assert form.count("btn-primary") == 1, form[:200]


def test_destructive_actions_use_the_danger_style(signed_in_client):
    _add_bike(signed_in_client)

    html = signed_in_client.get("/bikes/1").text

    delete_form = re.search(r'<form[^>]*action="/bikes/1/delete".*?</form>', html, re.S).group(0)
    assert "btn-danger" in delete_form and "btn-primary" not in delete_form


# --------------------------------------------------------------------- Polish

SEEDED_PAGES = [
    "/", "/components", "/maintenance/due", "/settings", "/bikes/new", "/bikes/1", "/bikes/1/edit",
    "/components/new", "/components/1", "/components/1/edit", "/bikes/1/maintenance",
    "/bikes/1/maintenance/new", "/components/1/maintenance", "/bikes/1/schedules/new",
    "/components/1/schedules/new", "/bikes/1/mileage/adjust", "/bikes/1/strava-pairing",
    "/schedules/1/edit", "/maintenance/1/edit",
]


def _seed_everything(client):
    _add_bike(client)
    _add_component(client, "Chain", "chain", parent_bike_id="1")
    client.post("/bikes/1/schedules", data={"name": "Service", "interval_days": "30"})
    client.post(
        "/bikes/1/maintenance", data={"description": "Lube", "performed_at": "2026-05-01"}
    )
    client.post(
        "/components/1/maintenance", data={"description": "Wax", "performed_at": "2026-05-02"}
    )


@pytest.mark.parametrize("path", SEEDED_PAGES)
def test_pages_have_clean_semantic_markup(signed_in_client, monkeypatch, path):
    from app.services import strava_client

    monkeypatch.setattr(strava_client, "get_athlete_gear", lambda token: [])
    _seed_everything(signed_in_client)

    response = signed_in_client.get(path)
    html = response.text

    assert response.status_code == 200, path
    assert re.search(r"<title>[^<]+</title>", html)
    assert html.count("<h1") == 1
    assert "<main" in html
    assert ' style="' not in html, "inline style attributes are not allowed"
    assert not re.search(r"<script(?![^>]*\bsrc=)", html), "inline scripts are not allowed"
    assert " onclick=" not in html


def test_maintenance_history_shows_a_table_and_an_empty_state(signed_in_client):
    _add_bike(signed_in_client)
    empty = signed_in_client.get("/bikes/1/maintenance").text
    assert 'class="empty-state"' in empty

    signed_in_client.post(
        "/bikes/1/maintenance", data={"description": "Lube chain", "performed_at": "2026-05-01"}
    )
    populated = signed_in_client.get("/bikes/1/maintenance").text
    assert '<th scope="col"' in populated and "Lube chain" in populated
    assert 'class="table-responsive"' in populated
