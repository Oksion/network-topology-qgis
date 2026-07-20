# Network Topology

**English** · [Русский](README.ru.md)

[![Build](https://github.com/Oksion/network-topology-qgis/actions/workflows/build-plugin.yml/badge.svg)](https://github.com/Oksion/network-topology-qgis/actions/workflows/build-plugin.yml)
[![Release](https://img.shields.io/github/v/release/Oksion/network-topology-qgis?sort=semver)](https://github.com/Oksion/network-topology-qgis/releases)
[![QGIS 4.0+](https://img.shields.io/badge/QGIS-4.0%2B-589632?logo=qgis&logoColor=white)](https://qgis.org)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![License: GPL v2+](https://img.shields.io/badge/License-GPLv2%2B-blue.svg)](LICENSE)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/3CLiAI1)

A **QGIS 4.0** plugin — a toolkit to **clean and build the topology of line networks**
(roads, rivers, pipelines, railways), preserving geometry and attributes.

> ⚠️ Requires **QGIS 4.0 or newer** (Qt6 / PyQt6). It will not load on QGIS 3.x.

## Why you'd want this

Line data from open (and not-so-open) sources — **OpenStreetMap**, digitized CAD/DWG,
scanned maps, GPS tracks — is drawn to *look* right, not to *be* topologically correct.
Two roads cross with no shared node, a stream stops a few centimetres short of the river
it feeds, an edge overshoots past a junction, the same road arrives as one long line here
and a dozen fragments there. On screen it's fine; as a **graph, it's broken**.

And almost everything useful you do with a line network needs that graph:

- **Routing / network analysis** — roads, transport, rail (pgRouting, GRASS `v.net`, QGIS network tools);
- **Hydrology** — connected river networks, flow tracing, catchments;
- **Utilities** — water, gas, power, sewer: connectivity and upstream/downstream tracing;
- **Any tree- or network-forming system** you need to build from raw lines.

If the source data isn't already noded and connected, those tools quietly give wrong
answers — a route that won't cross a junction, a "disconnected" island that's really a
30 cm gap.

**Network Topology** turns that raw geometry into a clean, connected graph: it extends
undershoots, trims overshoots, nodes every crossing and touch, and collapses redundant
pseudo-nodes — then lets you *inspect* the result (connected components, cluster extents,
node degrees) to confirm the network really is one connected whole. It bundles the
routine, fiddly steps — that otherwise mean chaining a dozen core/GRASS tools — into a
single QGIS Processing provider, keeping geometry and attributes intact throughout.

It's the **preprocessing & QA layer** you run *before* the domain-specific analysis: not a
replacement for your router or hydrology model, but the thing that makes them trustworthy.

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

### 6. Network nodes — `network_topology:networknodes`
One **point per node**, with its `degree` and a `node_type`: `dangle` (degree 1),
`pseudo` (degree 2), `junction` (degree 3+). The QA companion — spot dead-ends,
pseudo-nodes and real junctions.

```bash
qgis_process run "network_topology:networknodes" \
  --INPUT=roads_noded.gpkg --OUTPUT=nodes.gpkg
```

| Param | Meaning |
|-------|---------|
| `INPUT` | Line layer (node it first so endpoints meet at junctions) |
| `OUTPUT` | Points with `node_id`, `degree`, `node_type`, `edge_count` |

> Typical cleaning flow: **Resolve dangles** → **Topology split** → **Collapse pseudo-nodes**;
> then **Connected components** / **Cluster extents** / **Network nodes** to inspect topology.

## Installation

### From a packaged zip
1. Download `network_topology-<version>.zip` from the
   [latest release](https://github.com/Oksion/network-topology-qgis/releases/latest)
   (or build it yourself with `scripts/package.ps1`).
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

`0.2.0` — experimental. Geometry is treated as planar 2D (Z/M dropped). Long collinear
overlaps are noded only at their extremities; the dangle-extension pass is single-pass.
Validate on your own data before relying on it in production.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).

## Acknowledgements

Made with ❤️ and 🗺️ by [**Oksion**](https://github.com/Oksion), pair-programmed with
**Claude** (Anthropic) — from the first `metadata.txt` to the topology maths, the Russian
translation and this very CI.

If it saved you an afternoon of fixing dangles by hand, you can say thanks:

[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/3CLiAI1)
