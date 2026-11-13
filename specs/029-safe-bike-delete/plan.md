# Implementation Plan: 029 Safe Bike Delete

**Branch**: `029-safe-bike-delete` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary

Remove the delete section from `bikes/detail.html`, add a delete area to `bikes/form.html` (edit mode only) with a name field whose `pattern` equals the bike's name, style the button as unavailable until the form is valid (CSS `:has`, no script), and make `POST /bikes/{id}/delete` require `confirm_name` to equal the bike's name exactly. The match is checked in a service so the router stays thin.

## Technical Context

Python/FastAPI/Jinja2/HTMX as before; no migration; no JavaScript (constitution: vanilla JS only as the builder asset); tests in `tests/services`, `tests/routers`, `tests/test_ui_*`.

## Constitution Check (v1.3.0)

I Simplicity: native form validation plus one CSS rule instead of a script. II Modular: matching and pattern escaping in `app/services/confirmation_service.py`; the router only maps the error. III TDD: tests first. IV Security: server-side exact match on every delete; sign-in required; pattern text is HTML-escaped by Jinja and regex-escaped for the attribute; no SQL change. V Observability: log a line when a delete is refused for a wrong phrase and when a bike is deleted (ids only). Stack/layout unchanged. All pass.

## Source Code

```text
app/services/confirmation_service.py   # phrase_matches(expected, typed), html_pattern(expected)
app/services/bike_service.py           # delete_bike_with_name(bike_id, typed_name)
app/routers/bikes.py                   # delete route uses confirm_name; edit page shows the area and errors
app/templates/bikes/detail.html        # delete section removed
app/templates/bikes/form.html          # delete area (edit mode only)
app/templates/partials/forms.html      # field macro gains `pattern`
app/main.py                            # Jinja filter html_pattern
app/static/styles.css                  # unavailable look for the button until the form is valid
tests/ ...                             # mirrors
```

## Design Decisions

1. Exact, case-sensitive match against the saved name; no trimming.
2. Pattern escaping only escapes regular-expression syntax characters (`\ ^ $ . * + ? ( ) [ ] { } | /`), safe for browsers' pattern attribute handling; if a browser ever ignored the pattern, the server check still protects.
3. The earlier HTMX/full-page confirmation for bikes is removed; the generic confirm partial stays for parts.
