-- Moving time of a ride in whole seconds (specs/039-ride-moving-time); NULL when unknown.
ALTER TABLE ride_activity ADD COLUMN moving_time_seconds INTEGER
    CHECK (moving_time_seconds IS NULL OR moving_time_seconds > 0);
