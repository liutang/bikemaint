-- A bike is now described by year, make, model and category (specs/005-unified-bike-screen).
-- Bikes created earlier keep their single `name`; their year/make/model stay NULL.
-- The short-lived catalog reference is dropped.
ALTER TABLE bike ADD COLUMN year INTEGER;
ALTER TABLE bike ADD COLUMN make TEXT;
ALTER TABLE bike ADD COLUMN model TEXT;
ALTER TABLE bike DROP COLUMN catalog_id;
