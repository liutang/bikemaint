# Data Model: Unified Bike Screen and Simpler Parts

Migration `0007_bike_year_make_model.sql`: `ALTER TABLE bike ADD COLUMN year INTEGER; ADD COLUMN make TEXT; ADD COLUMN model TEXT; DROP COLUMN catalog_id`. Existing rows keep `name`/`bike_type`; year/make/model are NULL for them.

## Offered part kinds (display order) and parents

| Type | Parents | Several per parent |
|------|---------|--------------------|
| frame, fork, drivetrain, pedals, saddle, handlebar | bike | no |
| wheel, brake | bike | yes |
| tire | wheel (legacy: rim) | no |
| chain | bike, drivetrain | no |
| other | any | yes |

Legacy (hidden) kinds keep their previous parents: rim, hub, spoke, cassette, rotor, crankset, derailleur, shifter, pad, stem, seatpost, bolt. The offered kind `pedal` becomes `pedals` only in label; the stored type stays `pedal`.
