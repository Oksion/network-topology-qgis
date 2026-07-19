---
name: qgis4-plugin-dev
description: Conventions and pitfalls for building QGIS 4.0 (Qt6 / PyQt6) plugins — metadata.txt fields, the classFactory entry point, Processing providers/algorithms, and the Qt5→Qt6 changes (scoped enums, qgis.PyQt imports, exec() vs exec_(), no resources.qrc). Use when creating, editing, or migrating any QGIS 4 plugin code in this repo.
---

# Building QGIS 4.0 plugins (Qt6 / PyQt6)

QGIS 4.0 "Norrköping" moved the whole stack to **Qt6**; QGIS 4.x is **Qt6-only**
(no Qt5 fallback). Plugins are pure Python loaded from source.

## The five rules that matter most

1. **Import through the shim, not PyQt directly.**
   `from qgis.PyQt.QtCore import ...` / `from qgis.PyQt.QtGui import ...`.
   Never `import PyQt6...` directly — the shim is what keeps code portable and correct.
2. **Fully-scoped enums, everywhere.** Both Qt6 and QGIS 4.0's Python API require it:
   - `Qt.CheckState.Checked`, `Qt.AlignmentFlag.AlignLeft`, `QDialog.DialogCode.Accepted`
   - `Qgis.GeometryOperationResult.Success`, `QgsProcessing.SourceType.TypeVectorPolygon`,
     `QgsFeatureSink.Flag.FastInsert`, `QgsWkbTypes.GeometryType.PolygonGeometry`
   Unscoped access (`Qt.Checked`, `Qgis.Success`) raises/deprecates on Qt6.
3. **`exec()` not `exec_()`** — and `print` is fine, but the trailing-underscore Qt
   aliases (`exec_`, `print_`) are gone.
4. **No compiled resources.** Don't add `resources.qrc` + `pyrcc`. Load icons from a
   file path: `QIcon(os.path.join(os.path.dirname(__file__), "resources", "icon.svg"))`.
5. **`metadata.txt` targets 4.0 correctly** — see below. Do **not** set `supportsQt6`;
   it was a pre-release-only flag and was removed from QGIS core in 4.0 final.

## metadata.txt (QGIS-4-only plugin)

```ini
[general]
name=My Plugin
qgisMinimumVersion=4.0
description=One-line description.
version=0.1.0
author=Name
email=you@example.com
tags=comma,separated,no,spaces
experimental=True
hasProcessingProvider=yes   ; only for plugins that add Processing algorithms
```

- Dual 3.x + 4.0 support (not used in this repo) would instead be
  `qgisMinimumVersion=3.22` + `qgisMaximumVersion=4.99` and the `qgis.PyQt` shim
  everywhere. This project is **4.0-only** by decision.

## Entry point

`__init__.py` must expose `classFactory(iface)` returning the plugin object. Keep the
plugin-class import lazy inside the function so package import never fails at scan time.

```python
def classFactory(iface):
    from .my_plugin import MyPlugin
    return MyPlugin(iface)
```

The plugin object implements `initGui()` and `unload()` (and, for Processing plugins,
`initProcessing()`).

## Two plugin flavours

- **Processing plugin** (this repo): register a `QgsProcessingProvider` whose
  `loadAlgorithms()` adds `QgsProcessingAlgorithm` subclasses. No menu/toolbar needed.
  See `references/processing-algorithms.md`.
- **GUI plugin**: `initGui()` adds a `QAction` to a toolbar/menu; often a `QDialog` or
  `QgsDockWidget`, and/or a `QgsMapTool` for canvas interaction. Same Qt6 rules apply.

## References

- `references/qt6-migration.md` — the full Qt5→Qt6 change list + metadata details.
- `references/processing-algorithms.md` — anatomy of a Processing algorithm.

## Testing reality check

PyQGIS is **not** pip-installable. Tests that `import qgis` only run under QGIS's own
Python (or an OSGeo4W/conda `qgis` env). Guard them with
`pytest.importorskip("qgis.core")` so they skip — not error — elsewhere. Never claim a
bare `python` can import `qgis` without checking.

## Authoritative sources

- Migrate Your Plugin to QGIS 4 — https://plugins.qgis.org/docs/migrate-qgis4
- Qt5/Qt6 plugin compatibility wiki — https://github.com/qgis/QGIS/wiki/Plugin-migration-to-be-compatible-with-Qt5-and-Qt6
- "QGIS is moving to Qt6 and launching QGIS 4.0" — https://blog.qgis.org/2025/04/17/qgis-is-moving-to-qt6-and-launching-qgis-4-0/
