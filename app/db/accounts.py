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
