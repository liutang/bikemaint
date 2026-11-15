# Plan
- `component_history_service.parent_options` returns `[{"value","label"}]`: blank "None (on the bike or frame)", live parts except itself as "Name (Kind)" (with " #id" only for duplicates), plus the current parent marked "(deleted)" when needed.
- Router `_form_context` adds `parent_options`; template uses `select_field`.
- No route, request-model or schema change. Constitution: logic in service, tests mirror.
