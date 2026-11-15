# Feature Specification: Backup and Restore to a JSON File

**Feature Branch**: `067-backup-restore`
**Created**: 2026-11-15
**Input**: User testing feedback: add the ability to back up and re-import all data to a JSON file.

## User Scenarios & Testing
### User Story 1 - Download a Backup (Priority: P1)
1. **Given** Settings, **Then** a Backup and restore section has a Download backup button (`GET /settings/backup`) that downloads `bikemaint-backup-YYYY-MM-DD.json`.
2. **Given** the file, **Then** it holds every bike, part, install period, ride, mileage adjustment, maintenance entry, schedule, notification and sync rule, plus the non-secret settings (sync on/off and interval, time zone, clock format, mute, lead time). It never holds Strava tokens, the athlete id or the webhook URL.

### User Story 2 - Restore a Backup (Priority: P1)
1. **Given** Settings, **Then** a Restore form takes a backup file and a required "I understand this replaces all current data" checkbox.
2. **Given** a valid file and the checkbox, **Then** all current data is replaced by the file's (ids kept so links between records hold), settings are applied (the scheduler follows the sync settings), every mileage total is recomputed, and Settings shows how many bikes, parts and rides were restored.
3. **Given** the checkbox missing, a file that is not JSON, not a BikeMaint backup, from a newer version (unknown columns), too large, or inconsistent, **Then** nothing changes and a message says why (422).
4. **Given** a restore, **Then** the signed-in Strava account and its tokens and the webhook URL are untouched.

### Edge Cases
- Older backups missing newer columns restore with the column defaults.
- The restore is all or nothing.

## Requirements
- **FR-001**: `backup_service.export_backup()` / `restore_backup(data)` callable without FastAPI; format `{"app": "bikemaint", "format": 1, "schema": <last migration>, "exported_at": ..., "settings": {...}, "tables": {name: [row dicts]}}`.
- **FR-002**: Routes `GET /settings/backup` and `POST /settings/restore` (multipart `backup` file, `confirm`), sign-in required; upload limit 50 MB.
- **FR-003**: Restore validates before writing, runs in one transaction, and checks foreign keys.

## Success Criteria
- **SC-001**: Export, wipe and restore reproduces every record and every mileage total.

## Assumptions
- Tokens and the webhook URL are secrets and stay out of the file; the rider re-enters the webhook after restoring on a new install.
