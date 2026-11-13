# Implementation Plan: 009 App Icon and Reverse-Proxy Readiness

Stack and layout unchanged (constitution v1.3.0); no new dependency, table or migration.

- **Static assets**: `app/static/icons/` (SVG, 32 px, 192 px, 512 px, maskable 512 px, Apple touch icon) and `app/static/manifest.webmanifest`; served by the existing static mount, so no sign-in is required.
- **Templates**: `app/templates/layout.html` declares icons, manifest and light/dark theme colour for every page.
- **Proxy readiness**: `app/routers/auth.py` builds the Strava redirect address from `PUBLIC_BASE_URL` when set, otherwise from the proxy's forwarded headers, otherwise unchanged. Configuration documented in `.env.example` and README.
- **CI**: `.github/workflows/ci.yml` builds and publishes the image to GitHub Container Registry on merges to `master` (and, since 012, on a manual run on `master`).
- **Tests**: `tests/test_ui_icon.py` (assets, manifest, declarations, anonymous access, size budget), `tests/routers/test_auth.py` (redirect address cases).

## Constitution check
I Pass. II Pass (config read in the router layer is limited to building a URL; no business logic). III Pass by tests. IV Pass: secrets and public URL come from environment; cookie stays Secure. V N/A.
