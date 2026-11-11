"""Business logic for completing the Strava OAuth sign-in flow (FR-021)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account
from app.services import strava_client

logger = logging.getLogger(__name__)


def _iso_from_epoch(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def complete_strava_login(code: str) -> Account:
    """Exchange an OAuth authorization code for tokens and upsert the account row."""
    try:
        token_response = strava_client.exchange_code_for_token(code)
    except httpx.HTTPError as exc:
        # Never log the authorization code or any token — only what went wrong.
        logger.warning("Strava sign-in failed during token exchange error=%s", type(exc).__name__)
        raise
    with get_connection() as conn:
        account = accounts_db.upsert_from_strava(
            conn,
            strava_athlete_id=token_response["athlete"]["id"],
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            expires_at=_iso_from_epoch(token_response["expires_at"]),
        )
    logger.info(
        "Strava sign-in succeeded account_id=%s athlete_id=%s",
        account.id,
        account.strava_athlete_id,
    )
    return account
