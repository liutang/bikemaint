-- specs/079-archive-bikes-parts: when a bike or part was archived (UTC instant), NULL while active.
ALTER TABLE bike ADD COLUMN archived_at TEXT;
ALTER TABLE component ADD COLUMN archived_at TEXT;
