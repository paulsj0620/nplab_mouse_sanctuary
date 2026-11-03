# Python layout

Run commands from the project root with `python -m …`.

- `app/`: HTTP server, authentication and laboratory data service
- `imports/`: FACS summary and histology spreadsheet readers
- `statistics/`: ANOVA and Tukey comparisons
- `fcs/`: FCS analysis, gates, combine, WSP export, original-file storage and SMB access
- `maintenance/`: database and original-file backup/restore
- `deployment/`: Mac mini service and LAN setup
- `tests/`: Python regression tests
- `paths.py`: project root resolution

Start: `.venv/bin/python -m scripts.app.server`
All Python tests (both environments): `.venv/bin/python -m scripts.tests.run`
FCS engine tests require `.fcs-venv/bin/python`.

Static assets, configuration, vendor dependencies, databases and original data remain at their existing paths. `start.command` remains at the project root. Deployment launchers and generated service files remain in `deploy/`.
