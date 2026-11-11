-- maintenance_log_entry.kind: 'service' (work the rider logs or completes) or 'event' (parts
-- added or removed, recorded automatically). Events never count as "has maintenance history".
-- performed_time: optional HH:MM the rider typed; system-made entries use created_at instead.
ALTER TABLE maintenance_log_entry ADD COLUMN kind TEXT NOT NULL DEFAULT 'service';
ALTER TABLE maintenance_log_entry ADD COLUMN performed_time TEXT;
