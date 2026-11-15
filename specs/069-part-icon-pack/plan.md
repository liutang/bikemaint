# Plan
- Replace the 11 per-part macros and the borrowing map in `app/templates/partials/icons.html` with one data table inside `part()`: kind -> (inner SVG markup, style), styles `line` (stroke 2), `thin` (stroke 1.25), `solid` (fill currentColor). Generated shapes (chainring teeth, wheel-set spokes) are baked as static path data.
- Tests in `tests/test_ui_icons.py`: every catalog kind renders; offered kinds are distinct; fallbacks; decorative attributes; solid/thin styles. Old tests that encoded the 11 shared drawings are replaced deliberately.
- No new dependencies, routes or scripts; constitution unaffected (templates/static only). WCAG: icons are decorative and inherit `--link`, already contrast-tested.
