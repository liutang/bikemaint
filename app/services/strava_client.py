"""Strava API client: OAuth token exchange/refresh (research.md §2).

The token endpoint and auth-header construction are isolated here so that
Strava's scheduled API/auth changes (research.md §1 note) are a one-line update.
"""

from __future__ import annotations

import os

import httpx

STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"


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
