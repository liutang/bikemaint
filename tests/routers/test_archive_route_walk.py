"""Every POST route is classified for the archive lock (specs/079 T024).

A route either checks the lock (tested with a locked item in tests/routers/test_archive.py), is
allowed on a locked item by design, or is not about one bike or part. A new POST route fails this
test until it is put in one of the lists, so no route can skip the rule.
"""

import importlib
import pkgutil

import app.routers

CHECKS_THE_LOCK = {
    "/bikes/{bike_id}", "/bikes/{bike_id}/strava-pairing", "/bikes/{bike_id}/strava-reimport", "/bikes/{bike_id}/strava-unpair",
    "/builder/add", "/builder/move", "/builder/delete",
    "/components", "/components/{component_id}", "/components/{component_id}/move", "/components/{component_id}/delete",
    "/components/{component_id}/install-history", "/bikes/{bike_id}/install-history",
    "/install-periods/{period_id}", "/install-periods/{period_id}/delete",
    "/bikes/{bike_id}/maintenance", "/components/{component_id}/maintenance", "/maintenance/{entry_id}", "/maintenance/{entry_id}/delete",
    "/bikes/{bike_id}/mileage/adjust", "/components/{component_id}/mileage/adjust",
    "/bikes/{bike_id}/rides", "/rides/{ride_id}", "/rides/{ride_id}/delete",
    "/bikes/{bike_id}/schedules", "/components/{component_id}/schedules",
    "/schedules/{schedule_id}", "/schedules/{schedule_id}/complete", "/schedules/{schedule_id}/delete",
    "/bikes/{bike_id}/sync-rules", "/components/{component_id}/sync-rules",
    "/bikes/{bike_id}/archive", "/components/{component_id}/archive",
}
ALLOWED_ON_A_LOCKED_ITEM = {  # research §2
    "/bikes/{bike_id}/delete",  # the archived bike itself, typed-name confirmation
    "/bikes/{bike_id}/unarchive", "/components/{component_id}/unarchive",
}
NOT_ABOUT_ONE_BIKE_OR_PART = {
    "/bikes",  # creates a new, active bike
    "/logout", "/sync/strava", "/notifications/{notification_id}/acknowledge",
    "/settings/backup/run", "/settings/restore",
    "/settings/strava/reconnect", "/settings/strava/sync", "/settings/timezone", "/settings/clock",
    "/settings/notifications/mute", "/settings/notifications/test", "/settings/webhook", "/settings/notifications", "/settings/theme",
}


def _post_paths():
    paths = set()
    for module in pkgutil.iter_modules(app.routers.__path__):
        router = getattr(importlib.import_module(f"app.routers.{module.name}"), "router", None)
        for route in getattr(router, "routes", []):
            if "POST" in (getattr(route, "methods", None) or set()):
                paths.add(route.path)
    return paths


def test_every_post_route_is_classified_for_the_archive_lock():
    listed = CHECKS_THE_LOCK | ALLOWED_ON_A_LOCKED_ITEM | NOT_ABOUT_ONE_BIKE_OR_PART
    assert not (CHECKS_THE_LOCK & ALLOWED_ON_A_LOCKED_ITEM) and not (CHECKS_THE_LOCK & NOT_ABOUT_ONE_BIKE_OR_PART)
    paths = _post_paths()
    assert paths - listed == set(), "classify these POST routes for specs/079"
    assert listed - paths == set(), "these listed routes no longer exist"
