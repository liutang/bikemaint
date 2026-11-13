-- Parts being added or removed are no longer recorded as maintenance history (specs/022-install-history-split).
-- Install history (component_installation_period) holds the same facts, so the automatic entries go.
-- Only rows recorded as events are removed; work the rider logged or completed (kind = 'service') stays.
DELETE FROM maintenance_log_entry WHERE kind = 'event';
