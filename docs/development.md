# Development guide

## Requirements

- **QGIS 4.0+** installed (Qt6 build). On Windows the OSGeo4W installer or the
  standalone QGIS 4.0 installer both work.
- The plugin runs on QGIS's bundled Python (CPython 3.9+). You do **not** create a
  normal virtualenv for running it — QGIS supplies the interpreter and `qgis` module.

## Repository layout

See [../CLAUDE.md](../CLAUDE.md#project-layout) for the annotated tree.

## Fast dev loop

1. Deploy into your QGIS 4 profile:
   ```powershell
   ./scripts/deploy.ps1
   ```
2. Launch QGIS → **Plugins → Manage and Install Plugins** → enable **Topology Split**.
3. Install the **Plugin Reloader** plugin (once). After editing code, hit its reload
   button to reload without restarting QGIS.
4. The algorithm appears in the **Processing Toolbox** under
   **Topology Split → Topology → Topology split**.

## Running the algorithm headless

```bash
qgis_process run "topology_split:topologysplit" \
  --INPUT=parcels.gpkg \
  --SPLIT_LAYER=cut_lines.gpkg \
  --OUTPUT=out.gpkg
```

## Tests

The tests need a PyQGIS-capable interpreter. A plain `pip install pytest` does **not**
provide the `qgis` module — use QGIS's Python or an OSGeo4W/conda `qgis` env.

```powershell
# OSGeo4W shell (has qgis on the path):
python -m pytest

# or point at QGIS's python explicitly (adjust the path/version):
& "C:/Program Files/QGIS 4.0/apps/Python312/python.exe" -m pytest
```

Without PyQGIS, the tests **skip** (they don't fail) thanks to `pytest.importorskip`.

## Linting

```powershell
pip install -r requirements-dev.txt   # into any Python; ruff needs no qgis
ruff check .
ruff format .
```

## Packaging a release

```powershell
./scripts/package.ps1     # -> dist/topology_split-<version>.zip
```
Bump `version=` in `metadata.txt` and add a `CHANGELOG.md` entry first.

## QGIS 4 / Qt6 gotchas

The recurring pitfalls (scoped enums, `qgis.PyQt` imports, no `resources.qrc`,
`exec()` vs `exec_()`) are documented in the project skill:
[.claude/skills/qgis4-plugin-dev/SKILL.md](../.claude/skills/qgis4-plugin-dev/SKILL.md).
