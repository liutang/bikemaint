# Feature Specification: Dated Backup Names and Rolling Backups to a Volume

**Feature Branch**: `068-rolling-backups`
**Created**: 2026-11-15
**Input**: User testing feedback: manual backup files should include the date and time; add a backup volume (for example a mounted NAS) set in the Docker compose file, with a number N of rolling backups kept there (extends specs/067).

## User Scenarios & Testing
### User Story 1 - Dated Names (Priority: P1)
1. **Given** Download backup, **Then** the file is named `bikemaint-backup-YYYY-MM-DD-HHMMSS.json`, in the time zone saved in Settings.

### User Story 2 - Automatic Rolling Backups (Priority: P1)
1. **Given** the container has `BACKUP_DIR` set (a mounted volume), **Then** a backup file with the same dated name is written there every `BACKUP_INTERVAL_HOURS` (default 24) and after each is written only the newest `BACKUP_KEEP` (default 7) backup files remain; other files in the folder are never touched.
2. **Given** `BACKUP_DIR` unset, **Then** no automatic backups run and Settings says how to turn them on.
3. **Given** Settings with `BACKUP_DIR` set, **Then** a section shows the folder, how often, how many are kept and the stored backups (newest first), with a Back up now button that writes one immediately (and prunes), reporting the file name or the error (for example an unwritable folder).
4. **Given** a write failure, **Then** it is logged without secrets, nothing is pruned, and the app keeps running.
5. **Given** invalid values (`BACKUP_KEEP` or `BACKUP_INTERVAL_HOURS` not a whole number of at least 1), **Then** defaults are used and a warning is logged.

### Edge Cases
- Files are written to a temporary name and renamed, so a half-written file never counts as a backup.
- Two backups in the same second get a numeric suffix so none is overwritten.
- Backup files are the same JSON as the manual download and restore through the same form.

## Requirements
- **FR-001**: `backup_service.backup_filename(now)`, `rolling_config()`, `write_rolling_backup()` (write then prune), `list_rolling_backups()`.
- **FR-002**: A scheduler job `rolling_backup` when `BACKUP_DIR` is set; failures never propagate.
- **FR-003**: `POST /settings/backup/run` (sign-in required) and a Settings section.
- **FR-004**: README, `.env.example` and a compose example document the three variables.

## Success Criteria
- **SC-001**: With `BACKUP_KEEP=3`, after five backups exactly the newest three files remain.

## Assumptions
- The compose file is the rider's own; the repo documents the snippet. The folder must be writable by the container user.
