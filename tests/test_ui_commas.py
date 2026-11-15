"""Every displayed mileage has thousands separators (specs/059-comma-mileage)."""

from app.db import connection
from app.services import bike_service, component_service, maintenance_service, schedule_service


def _bike_with_miles(total=12345.6):
    bike = bike_service.create_bike(name="Madone", manual_baseline_mileage=total)
    chain = component_service.create_component(
        name="Chain", component_type="chain", parent_bike_id=bike.id, manual_baseline_mileage=2345.6
    )
    return bike, chain


def test_garage_bike_and_part_screens_group_thousands(signed_in_client):
    bike, chain = _bike_with_miles()
    storage = component_service.create_component(name="Spare", component_type="chain", manual_baseline_mileage=4321.0)

    assert "12,345.6 mi" in signed_in_client.get("/").text
    assert "12,345.6 mi" in signed_in_client.get(f"/bikes/{bike.id}").text
    assert "2,345.6 mi" in signed_in_client.get(f"/components/{chain.id}").text
    assert "4,321.0 mi" in signed_in_client.get("/components").text and storage.id


def test_rides_install_history_and_adjust_screens_group_thousands(signed_in_client):
    bike, chain = _bike_with_miles()

    rides = signed_in_client.get(f"/bikes/{bike.id}/rides").text
    assert "12,345.6 mi" in rides and "12,345.6</td>" in rides  # header total and the start row
    assert "2,345.6 mi in total" in signed_in_client.get(f"/components/{chain.id}/install-history").text
    assert "12,345.6 mi" in signed_in_client.get(f"/bikes/{bike.id}/mileage/adjust").text


def test_maintenance_history_and_form_hint_group_thousands(signed_in_client):
    bike, _ = _bike_with_miles()
    maintenance_service.log_maintenance(
        bike_id=bike.id, description="Clean", performed_at="2026-05-01", mileage_at_service=9876.5
    )

    history = signed_in_client.get(f"/bikes/{bike.id}/maintenance").text
    form = signed_in_client.get(f"/bikes/{bike.id}/maintenance/new").text

    assert "9,876.5 mi" in history and "12,345.6 mi" in form


def test_schedule_text_and_overdue_distances_group_thousands(signed_in_client):
    bike, _ = _bike_with_miles(total=3000)
    schedule_service.create_schedule(
        bike_id=bike.id, service_type="Lube/Wax", interval_kind="usage", interval_unit="miles", interval_value=1000
    )
    with connection.get_connection() as conn:
        conn.execute("UPDATE bike SET total_mileage = 9000")

    page = signed_in_client.get(f"/bikes/{bike.id}/schedules").text
    due = signed_in_client.get("/maintenance/due").text

    assert "Every 1,000 miles" in page and "5,000 mi over" in page
    assert 'aria-label="Overdue by 5,000 miles"' in due and ">5,000mi<" in due
    assert schedule_service.next_due_text(
        schedule_service.list_overview_for_owner("bike", bike.id)[0]
    ).startswith("Next due")


def test_small_values_are_unchanged(signed_in_client):
    bike = bike_service.create_bike(name="Madone", manual_baseline_mileage=548.3)

    assert "548.3 mi" in signed_in_client.get(f"/bikes/{bike.id}").text
