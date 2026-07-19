# CLAUDE.md — Topology Split (QGIS 4.0 plugin)

Guidance for Claude Code when working in this repository.

## What this is

A **QGIS 4.0** plugin that ships a **Processing algorithm** (`Topology split`). It has
no classic menu/toolbar GUI — everything runs through the Processing framework
(Toolbox, model builder, `qgis_process` CLI, batch mode).

The algorithm splits every feature of an input polygon/line layer by the geometries
of a "splitter lines" layer, preserving attributes on each resulting part.

## Target platform (hard constraints)

- **QGIS 4.0+ only.** `qgisMinimumVersion=4.0` in `metadata.txt`.
- **Qt6 / PyQt6.** QGIS 4.x is Qt6-only. There is **no** Qt5 fallback here.
- Do **not** add `supportsQt6` to `metadata.txt` — that was a pre-release-only flag,
  removed from QGIS core in the 4.0 final release; it is no longer recognised.

## Coding rules for this codebase

1. **Import through the QGIS shim, never PyQt directly.**
   Use `from qgis.PyQt.QtCore import ...`, `from qgis.PyQt.QtGui import ...`, etc.
   Do not `import PyQt6...` directly.
2. **Fully-scoped enums, always.** Qt6 and QGIS 4.0 both require scoped enum access:
   - `Qgis.GeometryOperationResult.Success` (not `Qgis.Success`)
   - `QgsProcessing.SourceType.TypeVectorPolygon` (not `QgsProcessing.TypeVectorPolygon`)
   - `QgsFeatureSink.Flag.FastInsert`
   - `Qt.CheckState.Checked`, `QDialog.DialogCode.Accepted` if any GUI is added later.
3. **`exec()` not `exec_()`** on Qt dialogs/loops (the trailing-underscore aliases are gone).
4. **No compiled resources.** Do not add a `resources.qrc` / `pyrcc` step. Load the icon
   from the file path (`os.path.join(os.path.dirname(__file__), "resources", "icon.svg")`).
5. Keep the package importable at scan time — plugin entry imports stay lazy inside
   `classFactory` (see `__init__.py`).
6. New Processing algorithms go in their own module and are registered in
   `topology_split_provider.py::loadAlgorithms`.

## Project layout

```
Topology_split/
├── __init__.py                     # classFactory(iface) — QGIS entry point
├── metadata.txt                    # plugin manifest (QGIS reads this)
├── topology_split_plugin.py        # registers/unregisters the Processing provider
├── topology_split_provider.py      # QgsProcessingProvider (groups algorithms)
├── topology_split_algorithm.py     # QgsProcessingAlgorithm — the split logic
├── resources/icon.svg              # provider + plugin icon
├── tests/                          # pytest tests (need a QGIS Python env)
├── scripts/                        # deploy.ps1 / package.ps1 (Windows)
├── docs/development.md             # dev environment & workflow
└── .claude/skills/qgis4-plugin-dev # reusable skill: QGIS 4 / Qt6 plugin know-how
```

## The algorithm's core (`topology_split_algorithm.py`)

- Builds a `QgsSpatialIndex` over the splitter lines so each input feature is only
  tested against nearby lines.
- Splits with `QgsGeometry.splitGeometry(points, topological=False, splitFeature=True)`,
  which **mutates the geometry in place** to the first part and returns the extra parts.
  We accumulate parts across every polyline of every relevant splitter.
- Copies source `fields()`/`attributes()` onto each output part.

If you extend it, keep the "collect splitters → index → per-feature split → write parts"
shape, and honour `feedback.isCanceled()` / `feedback.setProgress(...)`.

## Build / run / test

There is no build step (pure Python). See `docs/development.md` for the full setup.

- **Deploy to a local QGIS profile for manual testing:** `scripts/deploy.ps1`
- **Package a distributable zip:** `scripts/package.ps1`
- **Run tests:** `pytest` — but they require a Python interpreter with the `qgis`
  module available (QGIS's own Python, or an OSGeo4W/conda `qgis` env). A plain
  `pip install pytest` will NOT provide `qgis`; those tests skip/err without it.

Do not assume a bare `python` on PATH can `import qgis`. When asked to run tests,
first check whether `qgis` is importable and say so if it is not.

## Style

- `ruff` config lives in `pyproject.toml`. Match the existing docstring style.
- User-facing strings wrapped in `self.tr(...)` for future translation.
