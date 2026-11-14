# Implementation Plan: 041 Parts Card Icons Only

Template only: `app/templates/partials/builder.html` drops the `node.can_up`/`can_down` arrow forms and the `node.targets` Move to `<details>`; Garage and Trash stay. `builder_service` still computes `can_up`, `targets` etc. (unused by this card; left in place, covered by existing service tests). Tests first in `tests/routers/test_builder.py`: replace the reorder-arrows and move-icon tests with one asserting each row has only Garage and Trash buttons. Constitution v1.3.0: pass (template change, no new behavior or route).
