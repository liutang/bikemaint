-- Account-wide mute for due-soon notifications and webhook posts (specs/045-notification-test-and-mute).
ALTER TABLE account ADD COLUMN notifications_muted INTEGER NOT NULL DEFAULT 0 CHECK (notifications_muted IN (0, 1));
