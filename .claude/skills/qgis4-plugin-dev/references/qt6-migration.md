# QGIS 3 → QGIS 4 / Qt5 → Qt6 change list

Reference for writing new QGIS 4.0 code correctly and for migrating 3.x plugins.

## Imports

| Do | Don't |
|----|-------|
| `from qgis.PyQt.QtCore import Qt, QCoreApplication` | `from PyQt5.QtCore import ...` |
| `from qgis.PyQt.QtWidgets import QDialog` | `from PyQt6.QtWidgets import ...` (directly) |
| `from qgis.PyQt.QtGui import QIcon, QColor` | mixing PyQt5 and PyQt6 imports |

The `qgis.PyQt` shim resolves to PyQt6 under QGIS 4 and PyQt5 under QGIS 3, so shim-based
code is portable. This repo is 4.0-only, but still uses the shim as the convention.

## Enums — must be fully scoped on Qt6

Qt6 removed the implicit unscoped enum names; QGIS 4.0 also scopes its own Python enums.

| Qt5 style (broken on Qt6) | Qt6 / QGIS 4 style |
|---------------------------|--------------------|
| `Qt.Checked` | `Qt.CheckState.Checked` |
| `Qt.AlignLeft` | `Qt.AlignmentFlag.AlignLeft` |
| `Qt.Horizontal` | `Qt.Orientation.Horizontal` |
| `Qt.UserRole` | `Qt.ItemDataRole.UserRole` |
| `QDialog.Accepted` | `QDialog.DialogCode.Accepted` |
| `QMessageBox.Yes` | `QMessageBox.StandardButton.Yes` |
| `Qgis.Success` | `Qgis.GeometryOperationResult.Success` |
| `QgsProcessing.TypeVectorPolygon` | `QgsProcessing.SourceType.TypeVectorPolygon` |
| `QgsFeatureSink.FastInsert` | `QgsFeatureSink.Flag.FastInsert` |
| `QgsWkbTypes.PolygonGeometry` | `QgsWkbTypes.GeometryType.PolygonGeometry` |

If unsure of the scope name, inspect in the QGIS Python console:
`from qgis.PyQt.QtCore import Qt; print([m for m in dir(Qt) if 'Check' in m])`.

## Method / API changes

- `dialog.exec_()` → `dialog.exec()`; `loop.exec_()` → `loop.exec()`.
- `QApplication.exec_()` → `.exec()`.
- `QDateTime`, `QVariant` null handling is stricter — prefer real Python `None` and
  typed values; avoid relying on `QVariant()` sentinels.
- `QRegExp` is gone → use `QRegularExpression`.
- `.toString()`/enum int coercions that silently worked may now need explicit `.value`.

## Resources / icons

- Do **not** ship `resources.qrc` compiled with `pyrcc5`/`pyrcc6`. The `pyrcc` tool is
  not part of PyQt6.
- Load icons directly from disk:
  ```python
  import os
  from qgis.PyQt.QtGui import QIcon
  QIcon(os.path.join(os.path.dirname(__file__), "resources", "icon.svg"))
  ```

## metadata.txt

- `qgisMinimumVersion=4.0` for a 4.0-only plugin.
- For dual support: `qgisMinimumVersion=3.22` + `qgisMaximumVersion=4.99`.
- **Remove** any `supportsQt6=...` line — it was pre-release-only and is now ignored /
  rejected. Leaving it in is a common mistake copied from mid-2025 tutorials.
- `hasProcessingProvider=yes` for Processing plugins.

## Validation

The QGIS plugin repository runs a `pyqgis4-checker` (a.k.a. "Qt6 Check") on uploads and
reports files/lines needing changes (informational, non-blocking). A `pyqt5_to_pyqt6.py`
migration script exists for mechanical bulk conversion of legacy plugins.
