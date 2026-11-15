# Plan
- `app/templates/partials/icons.html`: replace `wrench()` (drop the scale transform) with the specs/069 wrench path; replace `settings()` with gear B: 6 trapezoid teeth (outer r 9.8, root r 7.0) plus a circle r 3.
- Tests in `tests/test_ui_icons.py`: wrench() inner drawing equals part('other'); settings() has a 24-point gear outline and a centre circle and no transform.
