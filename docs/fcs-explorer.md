# FCS Explorer — initial implementation

Open Mouse Sanctuary → FCS Explorer. This version shares original FCS/WSP files with all signed-in lab members. The My uploads filter is a convenience filter, not a privacy boundary. Original uploader and timestamp are recorded. No public sharing link or external publication has been added.

## Use

1. Select FCS/WSP files and choose Upload to shared library. Binary 2 MB chunks support resume: reselect the same unchanged file in the same browser/account after interruption. Completed originals have a SHA-256 and verified local mirror. Upload limits: FCS 2 GB; WSP 100 MB.
2. Select an FCS and optionally its WSP. Confirm the mouse ID (or leave unlinked) and organ. Create analysis version. File names must match exactly one WSP SampleNode and total events must agree. Workspace paths are never followed to load other files automatically.
3. Select a completed analysis. Choose channels or a gate. A selected gate displays its parent population; selected members are highlighted in scatter mode. Gate outlines use the same preprocessing coordinates as membership calculation. Scatter, density and histogram views are available. PNG export includes preview size and seed. Gate CSV includes full paths, reference and computed counts, source hashes and engine.
4. Counts use all events, while plots show a deterministic maximum of 20,000 parent events (seed 20261103). A hover reports the original 1-based event index. Gates with the same name in different branches retain distinct full paths.

## Files supplied by the user

Initial ingestion was performed by the assistant under the existing qa_admin account; these are shared lab originals, not uploads attributed to another user.

| File | Events | Original channels | Gates | Counts differing from WSP |
|---|---:|---:|---:|---:|
| Liver_146.fcs | 249802 | 20 | 43 | 32 |
| Liver_147.fcs | 443017 | 20 | 43 | 28 |

The WSP is EXP9_T cell combine.wsp (FlowJo 10.10.0, 101 sample definitions). Only the two supplied acquisitions were analyzed. WSP internal sample IDs 153/154 are explicitly distinct from mouse IDs 146/147. FCS / channel labels are mapped to FlowJo _ aliases in memory only, with collision checking. Original bytes are unchanged.

**These recomputed counts are not validated FlowJo-equivalent results.** Stored FlowJo reference counts and differences are visible, and CSV includes them. Differences are unresolved. Existing Excel-imported measurements, original roster, exclusions and analysis presets are unchanged. Event counts are not absolute cells/µL. No recomputed value is automatically written to existing measurements.

## Boundaries

- Imports existing 1D/2D RectangleGate and PolygonGate definitions and WSP compensation/transforms. Unsupported types fail explicitly; originals remain downloadable.
- Imported gates are read-only. Gate drawing/editing, applying templates to other samples, UMAP/t-SNE, spectral unmixing and private/external sharing are not implemented.
- Without WSP: acquisition channels with standard FCS gain/time preprocessing only. No compensation or display transform is guessed.
- With WSP: compensation and transforms come from that workspace; axes display transformed coordinates (not inverse-transformed FlowJo tick labels). Already-compensated exports need review; metadata alone does not establish their processing history.
- Analysis limits: 2 million events, 50 million input channel values, 100 million event×gate memberships, 60 million plot-coordinate values. Single analysis worker, queue limit 20, 15-minute job timeout. File storage limit and analysis limit are deliberately separate.
- Interrupted running jobs are requeued after restart into new artifact directories. Finished versions are immutable.

## Preservation and backup

`data/fcs/objects/<sha256>` stores immutable originals; `data/fcs/mirror/<sha256>` is a verified second local copy. Staged upload chunks are fsynced before offsets advance. Original catalogue rows cannot be updated/deleted. Only temporary failed-copy files can be cleaned up by the copy routine; original bytes are never removed by the feature.

Both copies are on the SAME Mac and are not protection against loss of the Mac/disk. SMB/off-device backup is NOT configured.

The existing daily backup now creates a SQLite snapshot and an adjacent `.assets.json` manifest. `backups/fcs-assets/` holds hash-verified referenced originals and completed analysis arrays; incomplete transfer prefixes are preserved for resume. Never distribute just the SQLite snapshot when FCS assets are present. Keep the manifest and referenced asset folders together.

`fcs_backup.restore_bundle(snapshot, new_destination)` restores only into a nonexistent destination, verifies all hashes, restores the DB and originals/mirror/analysis files, and refuses to overwrite a live directory. A real backup of the supplied three originals and both analyses was restored into a temporary separate directory and verified (11 referenced assets, plots readable). A restore is an offline maintenance action; do not point the live server to a restored copy without review.

## Implementation and tests

- `fcs_storage.py`: append-only file metadata, resumable upload, SHA-256 copies, durable offsets, serial queue, plot sampling.
- `fcs_worker.py`: isolated FlowKit 1.2.3 process. Uses a version-pinned preprocessing adapter for gate overlay coordinates.
- `static/fcs.js`: white desktop UI and Canvas rendering. Local resources only.
- `.fcs-venv/` + `requirements-fcs.txt`: separate pinned analysis environment; existing main NumPy/SciPy stack is unchanged.
- `fcs_backup.py`: asset manifest, copy verification and safe restore.
- New DB tables: `fcs_transfers`, `fcs_files`, `fcs_runs`. Original FCS/WSP bytes are files, not per-event SQLite rows.
- 31 service/unit tests, 3 HTTP tests and 18 existing chart tests passed. Large upload test exceeds the old 10 MB limit; resume/idempotence/ownership/CSRF/immutability/backup restore tested. Real-file verification checks all gate counts and parent membership; rectangle overlay coordinates match stored membership exactly. Browser verifies sample/gate switching and chart display.

## 2026-11-03 QA gate editor

FCS Explorer is now restricted to stable user IDs [1, 2, 3] (qa_admin, qa_editor, qa_viewer) in fcs_access.json. Missing/invalid config denies access. Other administrators do not bypass this restriction; renaming an account cannot grant access. All /api/fcs/* endpoints enforce it before body processing, including chunks/download/plot/edit. Login/me expose fcs_access; UI hides the tab. General export/audit omit FCS catalogue, runs and FCS events for non-QA users. Existing graph/data/import functionality remains available. Do not enable general release without the user's request.

Added 2D finite rectangle and polygon drawing and handle dragging. Select a population then New rectangle/New polygon to create a child; select an existing 2D gate then Edit selected gate to modify it. Axes are frozen during editing; Cancel discards only the draft. Enter a gate name and mandatory reason, then Save as new analysis. Each save queues a new immutable run with actor/time/reason/base_run and cumulative geometry changes in fcs_runs.edit_spec. Migration adds this nullable column plus an immutable update trigger. Finished runs and original FCS/WSP bytes remain unchanged. Full-event membership is recalculated for edited gates and descendants using the exact stored coordinate axes and FlowUtils polygon / FlowKit-style rectangle bounds (min inclusive, max exclusive). Child names/paths update after parent rename. Affected FlowJo reference comparisons are cleared; unchanged gates retain theirs. No attempt to fix unresolved FlowJo binning differences. New gates support all available axes; changing compensation/transforms, 1D/open-ended gate editing, deletion, WSP export and batch propagation are not implemented. Self-intersecting polygons and invalid geometry are rejected. Max 100 edits/lineage and existing memory limits remain.

Validation: 14 access/library/account HTTP+unit tests, 22 existing service/FACS/statistics tests, 2 isolated gate geometry tests; JS syntax checks. Actual 146/147 unchanged Cells geometry edits reproduced all 43 prior app counts each. Production browser saved an unchanged Cells analysis and a new QA rectangle check under Cells (156946 events); both are clearly recorded as QA verification versions, not biological results. Original four-file catalogue and 6978 measurements unchanged; completed prior analyses preserved. A pre-existing running user analysis completed normally during rollout. Before deployment backup: backups/pre-gate-editor-20261103T111250.sqlite plus asset manifest/bundle; prior source in backups/gate-editor-code-20261103T111250.

## Workspace layout (2026-11-03)

The desktop workspace follows the FlowJo v10 workflow. Select an FCS sample on the left, then select a population in its collapsible tree. The middle panel shows its parent events and gate overlay; the right inspector shows full-event counts and parent frequency. Use the breadcrumb or Parent button to navigate upward. Axis and display selectors sit around the plot.

The top ribbon provides Select, Rectangle, Polygon, Edit gate, navigation and exports. Edit gate opens name/reason/save controls in the inspector. Save creates a new immutable analysis version; Cancel discards the draft. Earlier runs remain available in Analysis version. Files & upload opens the original-file library; New analysis opens FCS/WSP selection. Access remains limited to approved QA accounts. This is a FlowJo-style interface, not full FlowJo feature or numerical equivalence.

## FlowJo files and shared-folder import

To return a saved analysis to FlowJo, select its version and click **FlowJo WSP**. Download the new WSP and original FCS into the same folder, then open the WSP in FlowJo v10. Reconnect the FCS if prompted. The export is retained in the file library and normal backups. Only the selected sample's saved edits are applied; the original workspace's other samples and group templates remain. Their FCS files may need reconnecting separately. Original files and older analyses are never overwritten.

This preview exports WSP-backed rectangle/polygon edits, including renamed gates and new child gates. Compensation and transforms remain those of the imported WSP. Every export is reimported to check geometry and hierarchy. Actual FlowJo application acceptance still needs verification; historical FlowJo count differences remain unresolved. WSP-free analyses and native FlowJo v11 .flowjo files are not supported by this export.

In **Files & upload**, select a workspace under **FCS files referenced by a workspace**, then click **Find referenced files**. The table shows its recorded paths and whether each source is available on the server. Search by sample name and click **Import from SMB**. This preserves a local copy and verified mirror; matching file hashes reuse existing library entries. Use **New analysis** to apply the selected WSP. No SMB source is moved or edited.

The confirmed mapping is S:/MK3/research/ → /Volumes/research/ in fcs_paths.json. Only server-configured roots are eligible, and the Mac must have the SMB share mounted. A browser cannot open arbitrary paths on a researcher's PC. WSP references do not grant access to paths outside the configured roots.

On the server's first SMB import, macOS may ask the Mac user to allow the Python server to access network volumes. An unanswered prompt can delay reading even when paths are visible. Imports time out after two minutes with guidance; approve the intended network-volume request on the Mac, then retry. No source is modified or partially published on timeout.
