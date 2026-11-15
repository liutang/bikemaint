"""Backup download and restore upload (specs/067-backup-restore).

Thin: reading, validating and restoring the file is `app/services/backup_service.py`.
"""

from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.routers.settings import _settings_page
from app.services import backup_service
from app.services.auth_dependency import require_account

router = APIRouter()


@router.get("/settings/backup", name="download_backup")
def download_backup(account=Depends(require_account)):
    body = json.dumps(backup_service.export_backup(), indent=1)
    name = f"bikemaint-backup-{date.today().isoformat()}.json"
    return Response(body, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


@router.post("/settings/restore", name="restore_backup")
async def restore_backup(request: Request, account=Depends(require_account)):
    form = await request.form()
    upload = form.get("backup")
    problem = None
    if form.get("confirm") != "on":
        problem = "Tick the box to confirm that the restore replaces all current data."
    elif upload is None or not hasattr(upload, "read"):
        problem = "Choose a backup file."
    else:
        try:
            counts = backup_service.restore_backup(backup_service.parse_backup(await upload.read()))
        except ValueError as exc:
            problem = str(exc)
    if problem:
        return _settings_page(request, account.id, {"errors": [problem], "field_errors": {"backup": problem}}, status_code=422)
    done = (
        f"Restored {_plural(counts['bike'], 'bike')}, {_plural(counts['component'], 'part')} and "
        f"{_plural(counts['ride_activity'], 'ride')}."
    )
    return _settings_page(request, account.id, {"restored": done})
