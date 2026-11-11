"""FastAPI app factory: session auth, static assets, templates, migrations (Phase 2)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db.connection import run_migrations
from app.routers import auth, bikes, components, mileage, settings
from app.services import scheduler
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
    app = FastAPI(lifespan=_lifespan)

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["SESSION_SECRET_KEY"],
        same_site="lax",
        https_only=True,
    )

    app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(AuthRequiredError)
    async def _auth_required_handler(request, exc: AuthRequiredError):
        return RedirectResponse(url="/login", status_code=303)

    app.include_router(auth.router)
    app.include_router(bikes.router)
    app.include_router(components.router)
    app.include_router(mileage.router)
    app.include_router(settings.router)

    return app


app = create_app()
