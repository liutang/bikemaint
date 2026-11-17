-- A maintenance entry's moment as a UTC instant, for comparing with rides and install periods
-- (specs/075). The date and time columns stay the rider's local ones; the one-time conversion
-- (data step 0019_typed_times_utc) fills this column for existing entries.
ALTER TABLE maintenance_log_entry ADD COLUMN performed_instant TEXT;
