-- specs/086: how much left makes a usage schedule due soon (miles, rides, hours), beside the days lead.
ALTER TABLE account ADD COLUMN lead_miles REAL NOT NULL DEFAULT 20;
ALTER TABLE account ADD COLUMN lead_rides INTEGER NOT NULL DEFAULT 2;
ALTER TABLE account ADD COLUMN lead_hours REAL NOT NULL DEFAULT 2;
