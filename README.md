# Network Topology

A **QGIS 4.0** plugin — a toolkit to **clean and build the topology of line networks**
(roads, rivers, pipelines, railways), preserving geometry and attributes.

> ⚠️ Requires **QGIS 4.0 or newer** (Qt6 / PyQt6). It will not load on QGIS 3.x.

Find the tools in the **Processing Toolbox** under **Network Topology → Topology**.

## Tools

### 1. Topology split — `network_topology:topologysplit`
Nodes a single line layer against itself: splits both lines at every **crossing** (X)
and where one line's **end touches** another line (T); optionally **extends a dangling
end** along its own direction, up to a **tolerance**, until it reaches another line.
Output = single-part LineStrings running node-to-node.

```bash
qgis_process run "network_topology:topologysplit" \
  --INPUT=roads.gpkg --TOLERANCE=0.5 --OUTPUT=roads_noded.gpkg
```

| Param | Meaning |
|-------|---------|
| `INPUT` | Line layer to node against itself |
| `TOLERANCE` | Max gap (map units) to extend a dangling end. `0` = no extension |
| `OUTPUT` | Noded single-part line layer |

### 2. Resolve dangles — `network_topology:resolvedangles`
Cleans dangling ends without splitting: **extends undershoots** along their direction and
**trims overshoots** back to the nearest crossing, within one tolerance. One output
feature per input feature.

```bash
qgis_process run "network_topology:resolvedangles" \
  --INPUT=roads.gpkg --TOLERANCE=1.0 \
  --FIX_UNDERSHOOTS=true --FIX_OVERSHOOTS=true --OUTPUT=roads_clean.gpkg
```

| Param | Meaning |
|-------|---------|
| `TOLERANCE` | Max gap to close / tail to trim (map units) |
| `FIX_UNDERSHOOTS` | Extend ends that stop short of a line |
| `FIX_OVERSHOOTS` | Trim ends that run past a crossing |

### 3. Collapse pseudo-nodes — `network_topology:collapsepseudonodes`
Merges chains of lines meeting only at **degree-2 nodes** into single lines
(junctions and dead-ends kept). Optional **group field** stops a merge across an
attribute boundary.

```bash
qgis_process run "network_topology:collapsepseudonodes" \
  --INPUT=roads_noded.gpkg --GROUP_FIELD=road_class --OUTPUT=roads_merged.gpkg
```

| Param | Meaning |
|-------|---------|
| `GROUP_FIELD` | (optional) only merge where this field is equal |
| `OUTPUT` | Merged single-part line layer |

### 4. Connected components — `network_topology:connectedcomponents`
Labels each line with the **independent sub-network** it belongs to: adds `cluster_id`
(ordered by size, `1` = largest network) and `cluster_size` (edge count). A clean network
is one component; extra components reveal gaps or stray features.

```bash
qgis_process run "network_topology:connectedcomponents" \
  --INPUT=roads_noded.gpkg --OUTPUT=roads_clusters.gpkg
```

| Param | Meaning |
|-------|---------|
| `INPUT` | Line layer (node it first for correct connectivity) |
| `OUTPUT` | Lines with `cluster_id` + `cluster_size` |

### 5. Cluster extents — `network_topology:clusterhulls`
One **polygon per connected sub-network**: convex hull, bounding box, or oriented
bounding box. Each carries `cluster_id`, `edge_count` and `length`. Use it to see where
disconnected clusters sit (a stray "island" far from the main network).

```bash
qgis_process run "network_topology:clusterhulls" \
  --INPUT=roads_noded.gpkg --METHOD=0 --OUTPUT=clusters.gpkg
```

| Param | Meaning |
|-------|---------|
| `METHOD` | `0` convex hull · `1` bounding box · `2` oriented bounding box |
| `OUTPUT` | One polygon per cluster (`cluster_id`, `edge_count`, `length`) |

> Typical cleaning flow: **Resolve dangles** → **Topology split** → **Collapse pseudo-nodes**;
> then **Connected components** / **Cluster extents** to inspect connectivity.

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
Then enable **Network Topology** in the Plugin Manager and use *Plugin Reloader* to
pick up code changes without restarting QGIS.

See [docs/development.md](docs/development.md) for the full dev setup.

## Status

`0.1.0` — experimental. Geometry is treated as planar 2D (Z/M dropped). Long collinear
overlaps are noded only at their extremities; the dangle-extension pass is single-pass.
Validate on your own data before relying on it in production.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
