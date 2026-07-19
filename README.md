# Topology Split

A **QGIS 4.0** plugin providing a Processing algorithm that **rebuilds the topology of
a single line layer against itself** — noding it at all intersections and touches,
optionally extending dangling ends, preserving geometry and attributes.

> ⚠️ Requires **QGIS 4.0 or newer** (Qt6 / PyQt6). It will not load on QGIS 3.x.

## What it does

Given **one line layer**, the algorithm:

1. Splits both lines at every **crossing** (X) and where one line's **end touches**
   another line (T).
2. Optionally **extends a dangling end** along its own direction, up to a configurable
   **tolerance**, until it meets another line — then splits there too.
3. Outputs **single-part** `LineString`s running node-to-node; the shape between nodes
   and all **attributes** are preserved.

Find it in the **Processing Toolbox** under **Topology Split → Topology → Topology split**,
or run it headless:

```bash
qgis_process run "topology_split:topologysplit" \
  --INPUT=roads.gpkg \
  --TOLERANCE=0.5 \
  --OUTPUT=roads_noded.gpkg
```

### Parameters

| Name | Meaning |
|------|---------|
| `INPUT` | Line layer to be noded against itself |
| `TOLERANCE` | Max distance (map units) to extend a dangling end to reach another line. `0` disables extension |
| `OUTPUT` | Resulting single-part line layer |

## Installation

### From a packaged zip
1. Run `scripts/package.ps1` to build `topology_split-<version>.zip`.
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.

### Without installing — from the QGIS Python Console
Paste [console/topology_split_console.py](console/topology_split_console.py) into the
QGIS **Python Console** (`Ctrl+Alt+P`). Select your line layer first (or set
`INPUT_LAYER`/`TOLERANCE` in the CONFIG block at the top), and it adds a noded
memory layer to the project — no plugin install required.

### For development (symlink/copy into your profile)
```powershell
./scripts/deploy.ps1        # copies the plugin into your QGIS 4 profile
```
Then enable **Topology Split** in the Plugin Manager and use *Plugin Reloader* to
pick up code changes without restarting QGIS.

See [docs/development.md](docs/development.md) for the full dev setup.

## Status

`0.1.0` — experimental. Geometry is treated as planar 2D (Z/M dropped). Long collinear
overlaps are noded only at their extremities; the dangle-extension pass is single-pass.
Validate on your own data before relying on it in production.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
