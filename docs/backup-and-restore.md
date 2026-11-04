# Automatic SMB backup

Currently **disabled at the user’s request**. The launchd service is unloaded and disabled across login/reboot; `config/backup.json` has `enabled: false`. The scheduled command, including `--force`, performs no backup while disabled. Existing backups remain untouched. Re-enable only after explicit user authorization.

The scheduled service creates a consistent SQLite snapshot plus local FCS originals, completed analyses, pending upload prefixes, `archives/`, and `config/`. Linked external FCS originals are recorded by path/hash; their bytes are not copied. They still require the school storage backup. Source code and environments are provisioned separately from GitHub and pinned requirements.

- Schedule: 03:00 in the Mac's local timezone. Hourly checks retry unsent snapshots and catch up after downtime. Login starts the service. The Mac must be on and the SMB share mounted under the configured mount path.
- Destination: `config/backup.json` (machine-local, gitignored).
- Local backup: `backups/`; transfer completion receipts: `*.complete.json.sent`.
- Status: `logs/backup-status.json`; errors: `logs/backup-error.log`.
- No automatic deletion or retention cleanup. Unchanged assets are reused and verified by SHA-256. Monitor available disk space as history grows.
- A `.complete.json` on SMB is published only after all its referenced files are verified. Keep it with its database, assets manifest, `fcs-assets/`, `extra-assets/`, and staging folders. Do not move only the SQLite file.
- SMB interruption retains local snapshots; partial transfers retry hourly. Network work is bounded to 30 minutes per snapshot. No share credentials are stored by the application.

Run from the project root:

```sh
.venv/bin/python -m scripts.maintenance.smb_backup run --force
```

Restore to a NEW empty location (the destination must not exist):

```sh
.venv/bin/python -m scripts.maintenance.smb_backup restore "/mounted/backup/lab-TIMESTAMP.sqlite.complete.json" "/new/restore-folder"
```

Restore verifies every asset hash and DB integrity, then recreates `data/`, `archives/`, and `config/`. It never overwrites the running application. Review restored machine-specific configuration, remount external originals, and provision application code/dependencies before switching the server to the restored copy. Keep restored account/session data private.
