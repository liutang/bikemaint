# Implementation Plan: 031 Screen Polish

Small template and service changes; no migration, no new dependency, no new route.

- **Cancel** (`app/routers/schedules.py`, `app/templates/schedules/form.html`): the form context carries `cancel_url` (owner's screen for new schedules, `/maintenance/due` for edit); the template uses it, including on the 422 re-render.
- **Place links** (`app/services/component_history_service.py`, `app/templates/components/install_history.html`, `app/templates/bikes/install_history.html`): history rows gain `place_url` (`/components/{id}` for an existing parent part, `/bikes/{id}` for an existing bike, otherwise none); templates link when present.
- **Rides** (`app/templates/rides/log.html`): drop the link in the starting row.

Constitution (v1.3.0): I Simplicity, II Modular (URLs decided in the service, rendering in templates), III TDD (tests first), IV Security (existing sign-in routes, no new input), V n/a. All pass.
