-- bike.catalog_id: the common-bike catalog entry a bike was created from (specs/004-bike-builder).
-- NULL for bikes created before the catalog existed ("legacy" bikes keep their typed name).
ALTER TABLE bike ADD COLUMN catalog_id TEXT;
