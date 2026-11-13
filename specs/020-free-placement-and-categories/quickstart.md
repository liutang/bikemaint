# Quickstart: 020 Free Placement and Categorised Palette

Contract: [contracts/ui-contract.md](contracts/ui-contract.md). Data: [data-model.md](data-model.md).

## Automated

```bash
.venv/bin/python -m pytest tests/models/test_component_kinds.py tests/services tests/routers/test_builder.py \
  tests/routers/test_component_rules.py tests/test_ui_builder_assets.py -q
```

## Manual

1. Open a bike. Expect five collapsed categories under "Add a new part".
2. Expand Brakes and Wheels together; collapse Brakes; Wheels stays open.
3. Drag Brake Pads onto the bike, then a Saddle onto a Tire, then a second Chain onto the bike. All succeed.
4. Drag a part onto one of its own sub-parts. Expect it refused.
5. Open an older bike with a "drivetrain" or "other part". It still shows and can be edited.
