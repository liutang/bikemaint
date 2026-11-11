"""FastAPI dependency gating every protected route on an authenticated session (FR-021)."""

from __future__ import annotations

from starlette.requests import Request

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account


class AuthRequiredError(Exception):
    """Raised by `require_account` when no valid session/account exists.

    `app/main.py` registers an exception handler that turns this into a
    redirect to `/login`, so routers can simply depend on `require_account`
    without handling the unauthenticated case themselves.
    """


def require_account(request: Request) -> Account:
    account_id = request.session.get("account_id")
    if account_id is None:
        raise AuthRequiredError()

    with get_connection() as conn:
        account = accounts_db.get_by_id(conn, account_id)

    if account is None:
        raise AuthRequiredError()

    return account
