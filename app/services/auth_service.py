"""Business logic for completing the Strava OAuth sign-in flow (FR-021)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account
from app.services import strava_client


def _iso_from_epoch(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def complete_strava_login(code: str) -> Account:
    """Exchange an OAuth authorization code for tokens and upsert the account row."""
    token_response = strava_client.exchange_code_for_token(code)
    with get_connection() as conn:
        return accounts_db.upsert_from_strava(
            conn,
            strava_athlete_id=token_response["athlete"]["id"],
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=_iso_from_epoch(token_response["expires_at"]),
        )
