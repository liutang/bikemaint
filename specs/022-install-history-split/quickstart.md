# Quickstart: 022 Install History Split

Contract: [contracts/routes.md](contracts/routes.md). Data: [data-model.md](data-model.md).

## Automated

```bash
.venv/bin/python -m pytest tests/db tests/services/test_component_service.py tests/services/test_component_history_service.py \
  tests/routers/test_component_history.py tests/routers/test_maintenance.py -q
```

## Manual (after pulling the new image)

1. Open a bike's Maintenance history. Any earlier "Added…/Removed…" lines are gone; services you logged remain.
2. Add a part to the bike, move it to storage, delete another part. Maintenance history stays unchanged.
3. Click "Install history" on the bike. Each of those actions appears as a row, newest first; the part still on the bike says "Still installed".
4. Click a part name: its own screen opens, whose Install History can be edited.
