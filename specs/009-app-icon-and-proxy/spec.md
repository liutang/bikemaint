# Feature Specification: App Icon and Reverse-Proxy Readiness

**Status**: Implemented on branch `009-app-icon-and-proxy`; amended by later PRs (see Amendments)

**Input**: "The app needs an icon. I'm also going to create an NPM (Nginx Proxy Manager) entry for https://bikemaint.hosts.the-tangs.com."

## User Scenarios & Testing
1. **Given** any page, including sign-in, **When** it loads, **Then** the app icon, manifest and theme colour are declared and the icon files load without signing in (`tests/test_ui_icon.py`).
2. **Given** the app behind a TLS proxy, **When** the rider starts Strava sign-in, **Then** the redirect address uses the public HTTPS address (`tests/routers/test_auth.py`).
3. **Given** a merge to `master` or a manual run of CI on `master`, **When** CI passes, **Then** the image is published.

## Requirements
- **FR-001**: Every page, including sign-in, declares an app icon: an SVG favicon, a 32 px PNG fallback, an Apple touch icon, and a web app manifest with 192 px, 512 px and maskable 512 px icons, so the app looks right in tabs, bookmarks and when added to a home screen.
- **FR-002**: The icon is amber on charcoal, follows the Cockpit theme and has no external references. *(Original bike drawing replaced by drop bars with a wrench head; see Amendments.)*
- **FR-003**: The browser chrome colour follows the light and dark themes.
- **FR-004**: Icon files are static assets served without sign-in (the sign-in page needs them).
- **FR-005**: Behind a TLS-terminating proxy the app builds its Strava redirect address from the public HTTPS address: via the proxy's forwarded headers, or an explicit `PUBLIC_BASE_URL` setting that takes precedence. Without either, behavior is unchanged.
- **FR-006**: Container images are built and published to GitHub Container Registry on every merge to `master`, and can also be republished by running the CI workflow by hand on `master` (for example after an Actions outage).

## Assumptions
- The proxy forwards `X-Forwarded-Proto` and `X-Forwarded-For`; `FORWARDED_ALLOW_IPS` lists the proxy's address (or `*` on a private network).
- The Strava callback domain is the public hostname; the session cookie stays Secure (HTTPS only).

## Amendments
- **2026-11 (PR #11, branch `010-new-app-icon`)**: the icon was redrawn as drop bars with a wrench head, amber (#FFA800) on charcoal. Covered by `test_the_svg_icon_is_drop_bars_with_a_wrench_head_amber_on_charcoal` in `tests/test_ui_icon.py`. FR-002 amended.
- **2026-11 (PR #13, branch `012-ci-manual-publish`)**: the publish job also runs on `workflow_dispatch` on `master` (`.github/workflows/ci.yml`). FR-006 amended. No automated test; verified by reading the workflow condition (CI configuration is not unit-testable here).
