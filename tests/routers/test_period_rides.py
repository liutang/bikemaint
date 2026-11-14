"""The Rides page of one install period (specs/053-period-rides)."""

import re

from app.db import accounts, components, connection, mileage as mileage_db
from app.services import bike_service, component_history_service, component_service, ride_service


def _rows(html):
    return re.findall(r"<tr[^>]*>.*?</tr>", html.split("<tbody>")[1], re.S)


def _setup():
    with connection.get_connection() as conn:
        account = accounts.get_singleton(conn)
        accounts.update_timezone(conn, account.id, "America/New_York")
    bike = bike_service.create_bike(name="Madone")
    part = component_service.create_component(name="Chain", component_type="chain")
    with connection.get_connection() as conn:
        for n, miles, when in ((1, 22.1, "2024-08-22T16:41:10.000000Z"), (2, 25.7, "2024-08-24T12:32:00.000000Z"),
                               (3, 5.0, "2024-09-01T12:00:00.000000Z")):
            mileage_db.upsert_ride_activity(
                conn, strava_activity_id=n, strava_gear_id="g", bike_id=bike.id, distance_miles=miles, occurred_at=when
            )
        period = components.insert_period(
            conn, part.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2024-08-22T12:51:00.000000Z", removed_at="2025-02-27T00:00:00.000000Z",
        )
    return bike, part, period


def test_the_period_rides_page_lists_only_its_rides_with_no_start_row(signed_in_client):
    bike, part, period = _setup()

    html = signed_in_client.get(f"/install-periods/{period.id}/rides").text

    rows = _rows(html)
    assert len(rows) == 2 and "Starting mileage" not in html
    assert "25.7" in rows[1] or "25.7" in rows[0]
    assert "30.7 mi" in html  # header total = sum of the listed rides
    assert "Chain" in html and "read-only" in html


def test_the_total_equals_the_miles_on_the_part_install_history(signed_in_client):
    bike, part, period = _setup()

    miles = component_history_service.describe_history(part.id)[0]["miles"]
    html = signed_in_client.get(f"/install-periods/{period.id}/rides").text

    assert f"{miles:.1f} mi" in html


def test_both_install_histories_offer_a_rides_button_for_each_period(signed_in_client):
    bike, part, period = _setup()

    part_page = signed_in_client.get(f"/components/{part.id}/install-history").text
    bike_page = signed_in_client.get(f"/bikes/{bike.id}/install-history").text

    assert f'href="/install-periods/{period.id}/rides"' in part_page
    assert f'href="/install-periods/{period.id}/rides?from_bike={bike.id}"' in bike_page


def test_the_breadcrumb_returns_to_the_right_install_history(signed_in_client):
    bike, part, period = _setup()

    from_part = signed_in_client.get(f"/install-periods/{period.id}/rides").text
    from_bike = signed_in_client.get(f"/install-periods/{period.id}/rides?from_bike={bike.id}").text

    assert f'href="/components/{part.id}/install-history"' in from_part
    assert f'href="/bikes/{bike.id}/install-history"' in from_bike


def test_a_period_with_no_rides_shows_an_empty_state(signed_in_client):
    bike, part, period = _setup()
    other = component_service.create_component(name="Cassette", component_type="cassette")
    with connection.get_connection() as conn:
        empty = components.insert_period(
            conn, other.id, parent_bike_id=bike.id, parent_component_id=None,
            installed_at="2020-01-01T00:00:00.000000Z", removed_at="2020-02-01T00:00:00.000000Z",
        )

    html = signed_in_client.get(f"/install-periods/{empty.id}/rides").text

    assert "No rides counted" in html


def test_unknown_period_is_404(signed_in_client):
    assert signed_in_client.get("/install-periods/999/rides").status_code == 404


def test_signed_out_goes_to_login(client):
    response = client.get("/install-periods/1/rides", follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == "/login"
