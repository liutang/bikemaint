"""FastAPI app factory: session auth, static assets, templates, migrations (Phase 2)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db.connection import run_migrations
from app.routers import auth, bikes, builder, components, maintenance, mileage, schedules, settings
from app.services import scheduler, sync_status_service
from app.services.auth_dependency import AuthRequiredError

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    run_migrations()
    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx logs each outbound request URL at INFO; webhook URLs (e.g. Discord's) embed a
    # secret token, so keep that logger quiet (Constitution Principle V: no secrets in logs).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # The auto-generated API docs would be reachable without a session (FR-021); this app
    # is server-rendered HTML for a single user, so they have no audience.
    app = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["SESSION_SECRET_KEY"],
        same_site="lax",
        https_only=True,
    )

    app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)
    app.state.templates.env.globals["last_sync_label"] = sync_status_service.last_sync_label
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(AuthRequiredError)
    async def _auth_required_handler(request, exc: AuthRequiredError):
        return RedirectResponse(url="/login", status_code=303)

    app.include_router(auth.router)
    app.include_router(bikes.router)
    app.include_router(builder.router)
    app.include_router(components.router)
    app.include_router(mileage.router)
    app.include_router(maintenance.router)
    app.include_router(schedules.router)
    app.include_router(settings.router)

    return app


app = create_app()
