# Implementation Plan: 044

`app/db/maintenance.py` `list_for_bike` and `list_for_component`: same sort keys, descending (and `id DESC`). Test first in `tests/routers/test_maintenance.py` (existing order test inverted, plus same-day and no-time cases). Constitution v1.3.0: pass.
