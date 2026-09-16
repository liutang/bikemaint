"""Auth routes: `GET /login`, `GET /auth/strava/callback`, `POST /logout` (FR-021).

Per Constitution Principle II, this module holds no business logic — it only
wires HTTP concerns (the session cookie, redirects, template rendering) to
`app/services/auth_service.py`.
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.services import auth_service

router = APIRouter()

STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_SCOPE = "activity:read_all"


def _strava_authorize_url(request: Request) -> str:
    params = {
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "redirect_uri": str(request.url_for("strava_callback")),
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": STRAVA_OAUTH_SCOPE,
    }
    return f"{STRAVA_AUTHORIZE_URL}?{urlencode(params)}"


@router.get("/login", name="login")
def login(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "login.html",
        {"strava_authorize_url": _strava_authorize_url(request)},
    )


@router.get("/auth/strava/callback", name="strava_callback")
def strava_callback(request: Request, code: str):
    account = auth_service.complete_strava_login(code)
    request.session["account_id"] = account.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
