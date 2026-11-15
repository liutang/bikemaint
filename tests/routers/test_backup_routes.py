"""Backup and restore routes (specs/067-backup-restore)."""

import json

from app.services import backup_service, bike_service


def test_routes_need_sign_in(client):
    assert client.get("/settings/backup", follow_redirects=False).headers["location"] == "/login"
    assert client.post("/settings/restore", follow_redirects=False).headers["location"] == "/login"


def test_settings_offers_download_and_restore(signed_in_client):
    html = signed_in_client.get("/settings").text

    assert "Backup and restore" in html and 'href="/settings/backup"' in html
    assert 'action="/settings/restore"' in html and 'enctype="multipart/form-data"' in html and 'name="confirm"' in html


def test_download_is_a_json_attachment(signed_in_client):
    bike_service.create_bike(name="Road")

    r = signed_in_client.get("/settings/backup")

    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert "bikemaint-backup-" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.json"')
    assert json.loads(r.text)["tables"]["bike"][0]["name"] == "Road"


def _post(client, raw, confirm=True):
    return client.post("/settings/restore", files={"backup": ("b.json", raw, "application/json")},
                       data={"confirm": "on"} if confirm else {})


def test_restoring_replaces_the_data_and_reports_counts(signed_in_client):
    bike_service.create_bike(name="Road")
    raw = json.dumps(backup_service.export_backup()).encode()
    bike_service.create_bike(name="Extra")

    r = _post(signed_in_client, raw)

    assert r.status_code == 200 and "Restored" in r.text and "1 bike" in r.text
    assert [b.name for b in bike_service.list_bikes()] == ["Road"]


def test_missing_confirmation_or_a_bad_file_changes_nothing(signed_in_client):
    bike_service.create_bike(name="Road")
    raw = json.dumps(backup_service.export_backup()).encode()

    assert _post(signed_in_client, raw, confirm=False).status_code == 422
    assert _post(signed_in_client, b"nope").status_code == 422
    assert signed_in_client.post("/settings/restore", data={"confirm": "on"}).status_code == 422
    assert [b.name for b in bike_service.list_bikes()] == ["Road"]
