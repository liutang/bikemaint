"""Strava API client: OAuth token exchange/refresh (research.md §2).

The token endpoint and auth-header construction are isolated here so that
Strava's scheduled API/auth changes (research.md §1 note) are a one-line update.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account

STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"


def _client_id() -> str:
    return os.environ["STRAVA_CLIENT_ID"]


def _client_secret() -> str:
    return os.environ["STRAVA_CLIENT_SECRET"]


def exchange_code_for_token(code: str) -> dict:
    """Exchange an OAuth authorization code for access/refresh tokens."""
    response = httpx.post(
        STRAVA_OAUTH_TOKEN_URL,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Mint a new access token from a previously issued refresh token."""
    response = httpx.post(
        STRAVA_OAUTH_TOKEN_URL,
        data={
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    return response.json()


class StravaGearAccessError(Exception):
    """Strava answered but left the gear list out: the token lacks the `profile:read_all` scope."""


def get_athlete_gear(access_token: str) -> list[dict]:
    """Fetch the connected athlete's Strava gear entries (research.md §2: `GET /athlete` → `bikes[]`).

    Strava only includes `bikes` when the token was granted `profile:read_all`; a missing key
    (as opposed to an empty list) means the rider must sign in again to approve that access.
    """
    response = httpx.get(
        f"{STRAVA_API_BASE_URL}/athlete",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    bikes = response.json().get("bikes")
    if bikes is None:
        raise StravaGearAccessError("Strava did not include the gear list (profile:read_all missing)")
    return bikes


def get_activities(
    access_token: str, *, after: int | None = None, per_page: int = 200
) -> list[dict]:
    """Fetch all of the athlete's activities, following Strava's pages until a short
    page comes back. `after` is an optional Unix cursor (incremental sync); omitted
    for a full-history backfill."""
    activities: list[dict] = []
    page = 1
    while True:
        params: dict[str, int] = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after
        response = httpx.get(
            f"{STRAVA_API_BASE_URL}/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        response.raise_for_status()
        batch = response.json()
        activities.extend(batch)
        if len(batch) < per_page:
            return activities
        page += 1


class StravaTokenRefreshError(Exception):
    """Raised when refreshing an expired/invalid Strava token fails."""


def _iso_from_epoch(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def _is_expired(expires_at: str) -> bool:
    return _parse_iso(expires_at) <= datetime.now(timezone.utc)


def ensure_fresh_access_token(account: Account) -> str:
    """Return a valid access token for `account`, refreshing it first if expired.

    On refresh failure (e.g. a revoked grant), marks `account.strava_connection_stale`
    so a sync can be skipped without losing previously synced data (Acceptance Scenario
    US2-3), then raises `StravaTokenRefreshError`.
    """
    if not _is_expired(account.strava_token_expires_at):
        return account.strava_access_token

    try:
        token_response = refresh_access_token(account.strava_refresh_token)
    except httpx.HTTPStatusError as exc:
        # A separate, already-committed transaction: raising below must not roll this back.
        with get_connection() as conn:
            accounts_db.mark_connection_stale(conn, account.id)
        raise StravaTokenRefreshError(str(exc)) from exc

    with get_connection() as conn:
        refreshed = accounts_db.update_tokens(
            conn,
            account.id,
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=_iso_from_epoch(token_response["expires_at"]),
        )
    return refreshed.strava_access_token
