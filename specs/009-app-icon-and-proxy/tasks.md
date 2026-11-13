# Tasks: 009 App Icon and Reverse-Proxy Readiness

- [x] T001 Icon set and web manifest (`app/static/icons/`, `app/static/manifest.webmanifest`; `tests/test_ui_icon.py`)
- [x] T002 Declare icons, manifest and theme colour on every page (`app/templates/layout.html`; `tests/test_ui_icon.py`)
- [x] T003 Public redirect address via `PUBLIC_BASE_URL` or forwarded headers (`app/routers/auth.py`, `.env.example`, README; `tests/routers/test_auth.py`)
- [x] T004 CI builds and publishes the image on merge to `master` (`.github/workflows/ci.yml`)
- [x] T005 Redraw icon as drop bars with a wrench head (PR #11, `app/static/icons/*`; `tests/test_ui_icon.py`)
- [x] T006 Allow manual republish from `master` via `workflow_dispatch` (PR #13, `.github/workflows/ci.yml`)
