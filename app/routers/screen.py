"""Shared rendering for the unified bike/part screen (specs/005-unified-bike-screen).

Not a router: `bikes`, `components` and `builder` all render the same screen (page or HTMX
fragment) for a root (`bike:ID` or `component:ID`), so the logic lives in one place.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from app.services import builder_service


def screen_url(root: str) -> str:
    kind, root_id = builder_service.parse_root(root)
    return f"/bikes/{root_id}" if kind == "bike" else f"/components/{root_id}"


def is_htmx(request: Request) -> bool:
    return request.headers.get("hx-request") == "true"


def render_screen(
    request: Request,
    root: str,
    *,
    message: str | None = None,
    confirm: dict | None = None,
    status_code: int = 200,
    fragment: bool | None = None,
):
    """The whole screen, or just the `#builder` fragment for HTMX requests."""
    try:
        view = builder_service.build_view(root)
    except ValueError:
        view = None
    if view is None:
        return PlainTextResponse("Not found", status_code=404)
    as_fragment = is_htmx(request) if fragment is None else fragment
    if as_fragment:
        template = "partials/builder.html"
    else:
        template = "bikes/detail.html" if view.bike is not None else "components/detail.html"
    context = {
        "view": view,
        "crumbs": view.crumbs,
        "bike": view.bike,
        "component": view.component,
        "message": message,
        "confirm": confirm,
        "errors": [],
    }
    return request.app.state.templates.TemplateResponse(
        request, template, context, status_code=status_code
    )


def redirect_to(request: Request, url: str) -> Response:
    """Send the browser to `url`: an HX-Redirect for HTMX requests, a 303 otherwise."""
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)
