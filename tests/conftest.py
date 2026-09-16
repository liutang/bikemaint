"""Test-wide defaults so modules that read config at import time (e.g. `app.main`,
which builds the FastAPI app — including the session secret — at module load)
can always be imported during collection, regardless of which test file runs first.

Individual tests override these (e.g. `DATABASE_PATH`) via `monkeypatch` as needed.
"""

import os

os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")
os.environ.setdefault("DATABASE_PATH", ":memory:")
