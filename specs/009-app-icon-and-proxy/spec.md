# Feature Specification: App Icon and Reverse-Proxy Readiness

**Status**: Implemented on branch `009-app-icon-and-proxy`

**Input**: "The app needs an icon. I'm also going to create an NPM (Nginx Proxy Manager) entry for https://bikemaint.hosts.the-tangs.com."

## Requirements
- **FR-001**: Every page, including sign-in, declares an app icon: an SVG favicon, a 32 px PNG fallback, an Apple touch icon, and a web app manifest with 192 px, 512 px and maskable 512 px icons, so the app looks right in tabs, bookmarks and when added to a home screen.
- **FR-002**: The icon is a bike (two wheels, frame, saddle, handlebar) in the dark ink colour on the amber accent; it follows the Cockpit theme and has no external references.
- **FR-003**: The browser chrome colour follows the light and dark themes.
- **FR-004**: Icon files are static assets served without sign-in (the sign-in page needs them).
- **FR-005**: Behind a TLS-terminating proxy the app builds its Strava redirect address from the public HTTPS address: via the proxy's forwarded headers, or an explicit `PUBLIC_BASE_URL` setting that takes precedence. Without either, behavior is unchanged.
- **FR-006**: Container images are built and published to GitHub Container Registry on every merge to `master`.

## Assumptions
- The proxy forwards `X-Forwarded-Proto` and `X-Forwarded-For`; `FORWARDED_ALLOW_IPS` lists the proxy's address (or `*` on a private network).
- The Strava callback domain is the public hostname; the session cookie stays Secure (HTTPS only).
