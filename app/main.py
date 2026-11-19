"""FastAPI app factory: session auth, static assets, templates, migrations (Phase 2)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import component_kinds
from app.services import archive_service, asset_service, clock_service, confirmation_service, format_service, ride_service
from starlette.middleware.sessions import SessionMiddleware

from app.db import mileage as mileage_db
from app.db.connection import get_connection, run_migrations
from app.routers import (
    archive,
    auth,
    backup,
    bikes,
    builder,
    component_history,
    components,
    maintenance,
    mileage,
    rides,
    schedules,
    settings,
    sync_rules,
)
from app.services import scheduler, sync_status_service
from app.services.auth_dependency import AuthRequiredError

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    run_migrations()
    with get_connection() as conn:
        # Totals follow the rides and periods as they are now (specs/015 FR-013 corrected how they match).
        mileage_db.recompute_all_component_totals(conn)
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
    app.state.templates.env.globals["sync_state"] = sync_status_service.sync_state
    app.state.templates.env.globals["sync_hover"] = sync_status_service.sync_hover  # specs/084
    app.state.templates.env.globals["sync_line"] = sync_status_service.sync_line
    app.state.templates.env.filters["kind_name"] = component_kinds.kind_name
    app.state.templates.env.globals["static_url"] = asset_service.static_url
    app.state.templates.env.globals["is_locked"] = archive_service.is_locked  # specs/079: hide change controls
    app.state.templates.env.filters["local_time"] = clock_service.format_utc
    app.state.templates.env.filters["to_local"] = clock_service.to_local
    app.state.templates.env.filters["duration"] = ride_service.format_duration
    app.state.templates.env.filters["num1"] = format_service.num1
    app.state.templates.env.filters["num0"] = format_service.num0
    app.state.templates.env.filters["html_pattern"] = confirmation_service.html_pattern
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(AuthRequiredError)
    async def _auth_required_handler(request, exc: AuthRequiredError):
        return RedirectResponse(url="/login", status_code=303)

    @app.exception_handler(archive_service.ArchivedError)
    async def _archived(request: Request, exc: archive_service.ArchivedError):
        """A change to a locked bike or part (specs/079 research §3): 409 with what is archived and what to do."""
        logging.getLogger(__name__).info("refused change to an archived item path=%s", request.url.path)
        return app.state.templates.TemplateResponse(
            request, "archived_refusal.html", {"message": str(exc)}, status_code=409
        )

    app.include_router(auth.router)
    app.include_router(bikes.router)
    app.include_router(builder.router)
    app.include_router(components.router)
    app.include_router(component_history.router)
    app.include_router(mileage.router)
    app.include_router(rides.router)
    app.include_router(maintenance.router)
    app.include_router(schedules.router)
    app.include_router(settings.router)
    app.include_router(backup.router)
    app.include_router(sync_rules.router)
    app.include_router(archive.router)

    return app


app = create_app()
