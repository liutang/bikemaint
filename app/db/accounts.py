"""Parameterized query functions for the account table."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.rows import Account


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_by_id(conn: sqlite3.Connection, account_id: int) -> Account | None:
    row = conn.execute("SELECT * FROM account WHERE id = ?", (account_id,)).fetchone()
    return Account.from_row(row) if row else None


def get_by_strava_athlete_id(
    conn: sqlite3.Connection, strava_athlete_id: int
) -> Account | None:
    row = conn.execute(
        "SELECT * FROM account WHERE strava_athlete_id = ?", (strava_athlete_id,)
    ).fetchone()
    return Account.from_row(row) if row else None


def get_singleton(conn: sqlite3.Connection) -> Account | None:
    """The app's one connected account (spec Assumptions: single-user, single account)."""
    row = conn.execute("SELECT * FROM account ORDER BY id LIMIT 1").fetchone()
    return Account.from_row(row) if row else None


def mark_connection_stale(conn: sqlite3.Connection, account_id: int) -> None:
    conn.execute(
        "UPDATE account SET strava_connection_stale = 1, updated_at = ? WHERE id = ?",
        (_now(), account_id),
    )


def update_tokens(
    conn: sqlite3.Connection,
    account_id: int,
    *,
    access_token: str,
    refresh_token: str,
    expires_at: str,
) -> Account:
    conn.execute(
        """
        UPDATE account
        SET strava_access_token = ?, strava_refresh_token = ?, strava_token_expires_at = ?,
            strava_connection_stale = 0, updated_at = ?
        WHERE id = ?
        """,
        (access_token, refresh_token, expires_at, _now(), account_id),
    )
    account = get_by_id(conn, account_id)
    assert account is not None
    return account


def upsert_from_strava(
    conn: sqlite3.Connection,
    *,
    strava_athlete_id: int,
    access_token: str,
    refresh_token: str,
    expires_at: str,
) -> Account:
    """Create the account on first sign-in, or refresh its tokens on a later one (FR-021)."""
    now = _now()
    existing = get_by_strava_athlete_id(conn, strava_athlete_id)
    if existing is None:
        conn.execute(
            """
            INSERT INTO account (
                strava_athlete_id, strava_access_token, strava_refresh_token,
                strava_token_expires_at, strava_connected_at, strava_connection_stale,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (strava_athlete_id, access_token, refresh_token, expires_at, now, now, now),
        )
    else:
        conn.execute(
            """
            UPDATE account
            SET strava_access_token = ?,
                strava_refresh_token = ?,
                strava_token_expires_at = ?,
                strava_connection_stale = 0,
                updated_at = ?
            WHERE strava_athlete_id = ?
            """,
            (access_token, refresh_token, expires_at, now, strava_athlete_id),
        )
    account = get_by_strava_athlete_id(conn, strava_athlete_id)
    assert account is not None
    return account


def update_webhook_url(conn: sqlite3.Connection, account_id: int, url: str | None) -> None:
    conn.execute(
        "UPDATE account SET notification_webhook_url = ?, updated_at = ? WHERE id = ?",
        (url, _now(), account_id),
    )


def update_lead_time_days(conn: sqlite3.Connection, account_id: int, days: int) -> None:
    conn.execute(
        "UPDATE account SET notification_lead_time_days = ?, updated_at = ? WHERE id = ?",
        (days, _now(), account_id),
    )


def update_sync_settings(
    conn: sqlite3.Connection, account_id: int, *, enabled: bool, interval_minutes: int
) -> None:
    conn.execute(
        "UPDATE account SET strava_sync_enabled = ?, strava_sync_interval_minutes = ?, "
        "updated_at = ? WHERE id = ?",
        (1 if enabled else 0, interval_minutes, _now(), account_id),
    )


def update_timezone(conn: sqlite3.Connection, account_id: int, timezone: str) -> None:
    conn.execute(
        "UPDATE account SET timezone = ?, updated_at = ? WHERE id = ?",
        (timezone, _now(), account_id),
    )


def mark_synced(conn: sqlite3.Connection, account_id: int) -> None:
    """Record that a Strava sync run just finished successfully (found rides or not)."""
    conn.execute(
        "UPDATE account SET strava_last_synced_at = ? WHERE id = ?", (_now(), account_id)
    )
