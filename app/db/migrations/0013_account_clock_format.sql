-- 12- or 24-hour clock for displayed times (specs/036-twelve-hour-clock). Display only.
ALTER TABLE account ADD COLUMN clock_format TEXT NOT NULL DEFAULT '12' CHECK (clock_format IN ('12', '24'));
