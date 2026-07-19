# CLAUDE.md — Topology Split (QGIS 4.0 plugin)

Guidance for Claude Code when working in this repository.

## What this is

A **QGIS 4.0** plugin that ships a **Processing algorithm** (`Topology split`). It has
no classic menu/toolbar GUI — everything runs through the Processing framework
(Toolbox, model builder, `qgis_process` CLI, batch mode).

The algorithm rebuilds the topology of a **single line layer against itself**:

1. Input is a line (polyline) layer.
2. Split where the **end of a line touches another line** (T-junctions).
3. **Preserve the original geometry** — no vertex is moved or dropped; the shape
   between nodes is kept.
4. Optionally **extend a dangling end** along its own direction, up to a configurable
   tolerance, until it reaches another line.
5. Split **both** lines at every **crossing** (X-intersections).
6. Output is **single-part** `LineString`s (never `MultiLineString`), one per span
   between two nodes.
7. **Attributes are inherited** by every resulting part.

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

Pipeline (order matters — extend before noding):

1. **Explode** every input feature to single-part polylines (lists of `QgsPointXY`),
   keeping a copy of the parent attributes on each.
2. **Extend dangles** (`_extend_end`): for each true dangle endpoint (one that does
   not already lie on another line), take the bearing of its last segment, cast a ray
   of length `tolerance`, and if it meets another line, append that meeting point.
   Then rebuild the geometries + `QgsSpatialIndex`.
3. **Collect nodes**: for each pair of lines whose bboxes overlap, `geom_i.intersection(geom_j)`;
   `_extract_points` flattens the result (Point/MultiPoint, and Line endpoints for
   collinear overlaps). Each node point is added to **both** lines' cut lists.
4. **Cut** (`_split_polyline`): map each node point to a distance-along-line via
   `lineLocatePoint`, then split the vertex list at those distances — inserting a
   vertex mid-segment or reusing an existing one. Original vertices are preserved.
5. **Write** one single-part `LineString` per span, copying the parent attributes.

Conventions to keep if you extend it:

- Geometry is planar **2D** (Z/M dropped) and the sink wkbType is `Qgis.WkbType.LineString`.
- `eps` is scaled to the data extent (`diag * 1e-9`); reuse it, don't hard-code a literal.
- Honour `feedback.isCanceled()` / `feedback.setProgress(...)` in every pass.
- The helpers `_dist`, `_extract_points`, `_split_polyline` are pure and module-level —
  unit-testable without a full QGIS app where possible.

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
