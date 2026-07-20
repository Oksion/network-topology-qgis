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
2. Launch QGIS → **Plugins → Manage and Install Plugins** → enable **Network Topology**.
3. Install the **Plugin Reloader** plugin (once). After editing code, hit its reload
   button to reload without restarting QGIS.
4. The algorithm appears in the **Processing Toolbox** under
   **Network Topology → Topology → Topology split**.

## Running the algorithm headless

```bash
qgis_process run "network_topology:topologysplit" \
  --INPUT=parcels.gpkg \
  --SPLIT_LAYER=cut_lines.gpkg \
  --OUTPUT=out.gpkg
```

## Tests

The tests need a PyQGIS-capable interpreter. A plain `pip install pytest` does **not**
provide the `qgis` module — use QGIS's Python or an OSGeo4W/conda `qgis` env.

```powershell
# Easiest: use the QGIS python launcher, which sets up the PyQGIS environment for you.
# (This machine has QGIS 4.2.0; adjust the version in the path to your install.)
& "C:/Program Files/QGIS 4.2.0/bin/python-qgis.bat" -m pytest

# If pytest isn't installed in QGIS's python, install it there first:
& "C:/Program Files/QGIS 4.2.0/bin/python-qgis.bat" -m pip install pytest
```

Do **not** run a bare `python -m pytest` — the system Python cannot `import qgis`.
Without PyQGIS the tests **skip** (they don't fail) thanks to `pytest.importorskip`.

The functional suite (`tests/test_topology_split_algorithm.py`) covers X-crossings,
T-touches, attribute inheritance, dangle extension, and multipart explode. It has been
run green against QGIS 4.2.0 (Qt6).

## Linting

```powershell
pip install -r requirements-dev.txt   # into any Python; ruff needs no qgis
ruff check .
ruff format .
```

## Localization (translations)

User-facing strings go through `self.tr(...)`. Russian lives in
`i18n/network_topology_ru.ts` (source) → `network_topology_ru.qm` (compiled, shipped).
`topology_split_plugin.py` loads the `.qm` for the QGIS UI language at plugin start.

Regenerate after adding/changing strings:

```powershell
# 1) Update the .ts from source (pylupdate6 needs QGIS's Qt6 env, so run it via python-qgis):
#    a tiny runner that sets argv and calls PyQt6.lupdate.pylupdate.main works reliably.
& "C:/Program Files/QGIS 4.2.0/bin/python-qgis.bat" tools/update_ts.py

# 2) Fill the new <translation> entries in i18n/network_topology_ru.ts

# 3) Compile to .qm with any Qt's lrelease (Qt5 or Qt6 both fine — .qm is stable):
& "C:/Program Files/FreeCAD 0.20/bin/lrelease.exe" `
    i18n/network_topology_ru.ts -qm i18n/network_topology_ru.qm
```

To add another language, copy the `.ts`, translate, compile to
`network_topology_<lang>.qm` — the loader picks it by `locale/userLocale`.

## Packaging a release

```powershell
./scripts/package.ps1     # -> dist/network_topology-<version>.zip
```
Bump `version=` in `metadata.txt` and add a `CHANGELOG.md` entry first. The zip
includes `i18n/` (the compiled `.qm`).

## QGIS 4 / Qt6 gotchas

The recurring pitfalls (scoped enums, `qgis.PyQt` imports, no `resources.qrc`,
`exec()` vs `exec_()`) are documented in the project skill:
[.claude/skills/qgis4-plugin-dev/SKILL.md](../.claude/skills/qgis4-plugin-dev/SKILL.md).
