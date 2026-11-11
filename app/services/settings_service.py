"""Business logic for account settings: outbound webhook URL and notification lead time (FR-023)."""

from __future__ import annotations

from app.db import accounts as accounts_db
from app.db.connection import get_connection
from app.models.rows import Account


def get_account(account_id: int) -> Account:
    with get_connection() as conn:
        account = accounts_db.get_by_id(conn, account_id)
    if account is None:
        raise LookupError(f"No account with id {account_id}")
    return account


def set_webhook_url(account_id: int, url: str | None) -> None:
    with get_connection() as conn:
        accounts_db.update_webhook_url(conn, account_id, url)


def set_lead_time_days(account_id: int, days: int) -> None:
    with get_connection() as conn:
        accounts_db.update_lead_time_days(conn, account_id, days)
