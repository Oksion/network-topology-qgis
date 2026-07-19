# Topology Split

A **QGIS 4.0** plugin providing a Processing algorithm that **topologically splits**
vector features by a layer of splitting lines, preserving attributes.

> ⚠️ Requires **QGIS 4.0 or newer** (Qt6 / PyQt6). It will not load on QGIS 3.x.

## What it does

Given an **input** polygon or line layer and a **split lines** layer, the algorithm
cuts each input feature wherever a splitting line crosses it and outputs the resulting
parts as separate features — each keeping the original feature's attributes.

Find it in the **Processing Toolbox** under **Topology Split → Topology → Topology split**,
or run it headless:

```bash
qgis_process run "topology_split:topologysplit" \
  --INPUT=parcels.gpkg \
  --SPLIT_LAYER=cut_lines.gpkg \
  --OUTPUT=parcels_split.gpkg
```

### Parameters

| Name | Meaning |
|------|---------|
| `INPUT` | Polygon or line layer to be split |
| `SPLIT_LAYER` | Line layer whose geometries do the cutting |
| `OUTPUT` | Resulting layer (geometry type matches the input) |

## Installation

### From a packaged zip
1. Run `scripts/package.ps1` to build `topology_split-<version>.zip`.
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.

### For development (symlink/copy into your profile)
```powershell
./scripts/deploy.ps1        # copies the plugin into your QGIS 4 profile
```
Then enable **Topology Split** in the Plugin Manager and use *Plugin Reloader* to
pick up code changes without restarting QGIS.

See [docs/development.md](docs/development.md) for the full dev setup.

## Status

`0.1.0` — experimental. The split logic is functional but not yet validated across
all geometry edge cases (self-intersections, multipart inputs, curved geometries).

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
