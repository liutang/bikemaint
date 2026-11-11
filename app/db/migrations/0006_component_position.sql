-- component.position: order among siblings under one parent (specs/004-bike-builder).
-- Existing rows keep their current order (by id) within each parent.
ALTER TABLE component ADD COLUMN position INTEGER NOT NULL DEFAULT 0;

UPDATE component SET position = (
    SELECT COUNT(*) FROM component AS earlier
    WHERE earlier.id < component.id
      AND earlier.is_deleted = 0
      AND earlier.parent_bike_id IS component.parent_bike_id
      AND earlier.parent_component_id IS component.parent_component_id
);
