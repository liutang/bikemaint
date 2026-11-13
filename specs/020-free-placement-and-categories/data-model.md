# Data Model: 020 Free Placement and Categorised Palette

No schema change and no migration.

## `component.component_type` (existing TEXT, unconstrained)

Existing values stay valid. The catalog (code, not DB) decides which are offered.

## Catalog (reference data in `app/models/component_kinds.py`)

Each kind: `type` (stored id), `name` (display), `category` (one of Accessories, Brakes, Drivetrain, Frame, Wheels, or none for legacy), `offered` (bool).

| Category | Offered kinds (type id → name) |
|---|---|
| Accessories | accessories → Accessories; apparel → Apparel; computer → Computer; lights → Lights |
| Brakes | brake → Brake; brake_cable → Brake Cable; brake_lever → Brake Lever; pad → Brake Pads; rotor → Rotor |
| Drivetrain | bottom_bracket → Bottom Bracket; cassette → Cassette; chain → Chain; chainrings → Chainrings; crankset → Crankset; derailleur → Derailleur; pedal → Pedals; shifter → Shift levers; shifter_cable → Shifter Cable |
| Frame | fork → Fork; frame → Frame; handlebar → Handlebar; handlebar_tape → Handlebar Tape; headset → Headset; saddle → Saddle; seatpost → Seatpost; shock → Shock; stem → Stem |
| Wheels | axle → Axle; hub → Hub; trainer → Trainer; tube → Tube; tire → Tire; wheel → Wheel; wheelset → Wheel Set |

Legacy, valid but not offered: `drivetrain`, `other`, `rim`, `spoke`, `bolt`.

Order within a category is the order above (the order the rider supplied).

## Removed concepts

- Per-kind allowed parents and the `multi` (several per parent) flag: gone. Any kind goes under any parent, any number of times.

## Retained rule

- A part is never placed under itself or inside its own sub-tree (checked in the service on every move).
