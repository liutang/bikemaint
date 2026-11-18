"""Backup to and restore from a JSON file (specs/067-backup-restore).

Callable without FastAPI (Constitution Principle II). The export is driven by the live schema
(`PRAGMA table_info`), so columns added by later migrations are included automatically. Strava
tokens, the athlete id and the webhook URL are secrets and are never exported or overwritten.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db import accounts as accounts_db
from app.db import mileage as mileage_db
from app.db import typed_times
from app.db.connection import MIGRATIONS_DIR, get_connection

logger = logging.getLogger(__name__)

FORMAT = 2  # 2: every time is UTC (specs/075); 1 held typed times as typed
READABLE_FORMATS = (1, 2)
MAX_BYTES = 50 * 1024 * 1024

# Parents before children; restore deletes in the reverse order.
TABLES = (
    "bike", "component", "component_installation_period", "ride_activity", "mileage_adjustment",
    "maintenance_log_entry", "maintenance_schedule", "notification", "sync_rule",
)
# Account columns that are settings (not secrets).
SETTINGS = (
    "strava_sync_enabled", "strava_sync_interval_minutes", "timezone", "clock_format",
    "notifications_muted", "notification_lead_time_days",
)


def _zone_or_utc(name: str | None) -> str:
    try:
        ZoneInfo(name or "UTC")
    except Exception:
        return "UTC"
    return name or "UTC"


def _columns(conn, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]


def export_backup() -> dict:
    """Everything the rider entered or synced, as plain JSON-able data."""
    with get_connection() as conn:
        tables = {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in TABLES}
        account = conn.execute("SELECT * FROM account LIMIT 1").fetchone()
        settings = {k: account[k] for k in SETTINGS} if account else {}
    return {
        "app": "bikemaint",
        "format": FORMAT,
        "schema": max((p.name for p in MIGRATIONS_DIR.glob("*.sql")), default=""),
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "settings": settings,
        "tables": tables,
    }


def parse_backup(raw: bytes) -> dict:
    """The decoded backup, or ValueError saying why the file is not a usable BikeMaint backup."""
    if len(raw) > MAX_BYTES:
        raise ValueError("That file is too large to be a backup (limit 50 MB).")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("That file is not valid JSON.") from None
    if not isinstance(data, dict) or data.get("app") != "bikemaint":
        raise ValueError("That file is not a BikeMaint backup.")
    if data.get("format") not in READABLE_FORMATS:
        raise ValueError(
            f"Unsupported backup format {data.get('format')!r}; this version reads formats 1 and {FORMAT}."
        )
    if not isinstance(data.get("tables"), dict):
        raise ValueError("That backup has no data tables.")
    return data


def _check_rows(conn, data: dict) -> None:
    for table, rows in data["tables"].items():
        if table not in TABLES:
            raise ValueError(f"The backup has an unknown table '{table}': it was made by a newer version.")
        if not isinstance(rows, list):
            raise ValueError(f"The backup's '{table}' is not a list.")
        allowed = set(_columns(conn, table))
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"A row of '{table}' is not an object.")
            extra = set(row) - allowed
            if extra:
                raise ValueError(
                    f"'{table}' has columns this version does not know ({', '.join(sorted(extra))}): "
                    "the backup was made by a newer version."
                )
            for value in row.values():
                if value is not None and not isinstance(value, (int, float, str)):
                    raise ValueError(f"A value in '{table}' is not a plain number or text.")


def restore_backup(data: dict) -> dict[str, int]:
    """Replace all data with the backup's, all or nothing; returns rows restored per table."""
    import sqlite3

    counts: dict[str, int] = {}
    with get_connection() as conn:
        _check_rows(conn, data)
        conn.execute("PRAGMA defer_foreign_keys = ON")
        for table in reversed(TABLES):
            conn.execute(f"DELETE FROM {table}")
        try:
            for table in TABLES:
                rows = data["tables"].get(table, [])
                for row in rows:
                    cols = list(row)
                    conn.execute(
                        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                        [row[c] for c in cols],
                    )
                counts[table] = len(rows)
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("The backup is inconsistent: some records point at records that are not in it.")
        except sqlite3.Error as exc:
            raise ValueError(f"The backup could not be restored: {exc}") from None
        settings = {k: v for k, v in (data.get("settings") or {}).items() if k in SETTINGS}
        if settings:
            conn.execute(
                f"UPDATE account SET {', '.join(f'{k} = ?' for k in settings)}", list(settings.values())
            )
        if data.get("format") == 1:  # typed times as typed: convert with the backup's own zone (specs/075 FR-009)
            counts_converted = typed_times.convert(conn, _zone_or_utc(settings.get("timezone")))
            logger.info(
                "converted an older backup's typed times %s",
                " ".join(f"{table}={n}" for table, n in counts_converted.items()),
            )
        repaired = typed_times.repair_short_years(conn, typed_times.saved_zone(conn))  # specs/076 FR-007
        if any(repaired.values()):
            logger.info("repaired short years in a backup %s", " ".join(f"{table}={n}" for table, n in repaired.items()))
        for (bike_id,) in conn.execute("SELECT id FROM bike").fetchall():
            mileage_db.recompute_bike_total_mileage(conn, bike_id)
        mileage_db.recompute_all_component_totals(conn)
        account = accounts_db.get_singleton(conn)
    if account is not None:
        from app.services import scheduler, settings_service

        scheduler.apply_sync_settings(
            bool(account.strava_sync_enabled), settings_service.effective_sync_interval(account)
        )
    logger.info("backup restored %s", counts)
    return counts


# ---- dated names and rolling backups (specs/068-rolling-backups) ----

_NAME = re.compile(r"^bikemaint-backup-\d{4}-\d{2}-\d{2}-\d{6}(-\d+)?\.json$")


def backup_filename(now: datetime | None = None) -> str:
    """`bikemaint-backup-YYYY-MM-DD-HHMMSS.json` in the zone saved in Settings."""
    from app.services import clock_service

    moment = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(clock_service.zone_name()))
    return f"bikemaint-backup-{moment.strftime('%Y-%m-%d-%H%M%S')}.json"


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
        if value >= 1:
            return value
    except ValueError:
        pass
    logger.warning("%s must be a whole number of at least 1; using %s", name, default)
    return default


def rolling_config() -> tuple[Path, int, int] | None:
    """(folder, how many to keep, interval in hours) from the environment, or None when off."""
    folder = os.environ.get("BACKUP_DIR", "").strip()
    if not folder:
        return None
    return Path(folder), _positive_int("BACKUP_KEEP", 7), _positive_int("BACKUP_INTERVAL_HOURS", 24)


def list_rolling_backups() -> list[Path]:
    """Backup files in the configured folder, newest first (names sort by time)."""
    config = rolling_config()
    if config is None or not config[0].is_dir():
        return []
    return sorted((p for p in config[0].iterdir() if p.is_file() and _NAME.match(p.name)), key=lambda p: p.name, reverse=True)


def write_rolling_backup(now: datetime | None = None) -> Path:
    """Write one backup to the folder, then keep only the newest N. Raises OSError if it cannot write."""
    config = rolling_config()
    if config is None:
        raise ValueError("BACKUP_DIR is not set.")
    folder, keep, _ = config
    name = backup_filename(now)
    target = folder / name
    suffix = 1
    while target.exists():
        suffix += 1
        target = folder / name.replace(".json", f"-{suffix}.json")
    temporary = folder / (target.name + ".tmp")
    temporary.write_text(json.dumps(export_backup(), indent=1), encoding="utf-8")
    os.replace(temporary, target)
    for old in list_rolling_backups()[keep:]:
        old.unlink()
    logger.info("rolling backup written file=%s kept=%s", target.name, keep)
    return target


def describe_rolling_backups(today: "date | None" = None) -> list[dict]:
    """Backups in the folder, newest first, with how old each is ("today", "yesterday", "3 days ago")."""
    from datetime import date as _date

    from app.services import clock_service

    zone = ZoneInfo(clock_service.zone_name())
    day = today or datetime.now(zone).date()
    rows = []
    for path in list_rolling_backups():
        made = datetime.fromtimestamp(path.stat().st_mtime, zone).date()
        days = (day - made).days
        age = "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"
        rows.append({"name": path.name, "age": age})
    return rows
