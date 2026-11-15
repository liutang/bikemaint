# Plan
Jinja filters `num1` and `num0` (`app/services/format_service.py`) replace every `"%.1f"|format(...)` and `"%.0f"` mileage format in templates; `schedule_service._count`, `next_due_text` and `notification_service` use the same helpers. Inputs and stored values are untouched. Tests: `tests/services/test_format_service.py`, `tests/test_ui_commas.py`.
