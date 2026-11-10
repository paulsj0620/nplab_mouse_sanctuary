# Run the current data on Windows

1. Install 64-bit Python 3.12 from python.org with the Python launcher (`py`).
2. Extract the complete transfer ZIP to a local folder, such as `C:\MouseSanctuary`. Do not run inside the ZIP, an SMB share or a cloud-synced folder.
3. Double-click `start-windows.cmd`. The first launch installs the main application dependencies and needs internet access.
4. After the console prints the server address, open http://127.0.0.1:8000/ and sign in with your existing account. Keep the console open; Ctrl+C stops it.

The transfer contains a consistent SQLite snapshot, uploaded spreadsheets, accounts, saved graph settings/history, local FCS assets and archives. It is a separate copy: subsequent edits on Windows and the Mac do not synchronize. Do not overwrite one database with the other to merge changes. The existing Mac server and its files are unchanged. Automatic backups remain disabled.

The ZIP contains private research data and account password hashes. Transfer it directly using your own drive or approved private storage; do not commit it to GitHub.

## QA-only FACS

Graph, Data and spreadsheet Import use the main environment. The experimental FACS workspace remains QA-only. Local FCS files and previous analysis caches are included for preservation, but the FACS analysis environment is not installed by the Windows launcher and has not been validated on Windows. Use FlowJo for analysis for now.

SMB-linked originals are not copied. Their immutable references remain in the database. `config/fcs_paths.json` in the transfer maps the original `S:/MK3/research/` paths to `//med.tu-dresden.de/ste/MK3/research/`. Authenticate to that share in Windows before accessing linked originals. Network reachability still depends on the school network/VPN. The Mac configuration is not changed.

## Integrity

`TRANSFER-MANIFEST.json` lists SHA-256 hashes for the transfer payload and records its database snapshot counts. All ZIP entries were read back and verified when packaging. Windows execution itself must still be checked on the destination computer. No Mac virtual environment is copied; Windows creates its own environment.
