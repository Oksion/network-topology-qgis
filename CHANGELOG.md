# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.2] - 2026-07-20
### Changed
- Code cleanup before the plugins.qgis.org submission: linted and formatted the whole
  codebase with `ruff` (import order, f-strings outside `tr()`, line lengths, dead
  variable in `pseudonode_collapse`). No behaviour changes; translations unaffected
  (all 54 messages re-verified, `.qm` rebuilt).
- Tests: keep the `QgsProcessingContext` alive in the topology-split suite so its
  memory output layer is not garbage-collected mid-test (26/26 green on QGIS 4.2).

## [0.2.1] - 2026-07-20
### Changed
- Marked the plugin **stable** (`experimental=False`) after validation on real QGIS 4.2
  data — it now appears in the Plugin Manager without the "Show experimental" toggle.
- Inlined the version history into `metadata.txt`'s `changelog` field so it renders on
  the plugins.qgis.org listing page.

## [0.2.0] - 2026-07-20
### Changed
- **Renamed the plugin/provider to "Network Topology"** (provider id `network_topology`)
  to reflect its scope: cleaning and building the topology of line networks (roads,
  rivers, pipelines, railways). Algorithm ids are now `network_topology:*`.

### Added
- **Russian localization** (`i18n/network_topology_ru.ts` / `.qm`): all algorithm
  names, groups, parameter labels, help and messages. The plugin installs a
  `QTranslator` for the current QGIS UI language at load. `tools/update_ts.py`
  regenerates the source strings.
- **Resolve dangles** algorithm (`network_topology:resolvedangles`): directionally
  extend undershooting dangles and trim overshooting ones, under one tolerance with
  independent toggles; one output feature per input feature.
- **Collapse pseudo-nodes** algorithm (`network_topology:collapsepseudonodes`): merge
  chains of lines through degree-2 nodes into single lines, with an optional
  attribute-group barrier; attributes inherited from the longest segment.
- **Connected components** algorithm (`network_topology:connectedcomponents`): label
  each line with a `cluster_id` (and `cluster_size`) for its independent sub-network;
  ids ordered by size (1 = largest). Reveals disconnected clusters / gaps.
- **Cluster extents** algorithm (`network_topology:clusterhulls`): one polygon per
  connected sub-network — convex hull, bounding box, or oriented bounding box — with
  `cluster_id`, `edge_count` and `length`. Shared `build_components` helper in
  `topology_utils.py`.
- **Network nodes** algorithm (`network_topology:networknodes`): one point per node
  with `degree` and `node_type` (`dangle`/`pseudo`/`junction`, fixed English codes) —
  the QA companion to the cleaning tools.
- Shared helpers extracted into `topology_utils.py`.
- pytest suites for the new algorithms (green on QGIS 4.2).

## [0.1.0] - 2026-07-19
### Added
- Initial scaffold for QGIS 4.0 (Qt6 / PyQt6).
- Processing provider `Topology Split` with the `Topology split` algorithm that
  self-nodes a single line layer:
  - splits both lines at every crossing (X) and endpoint-touch (T);
  - optionally extends dangling ends along their bearing, up to a tolerance, until
    they meet another line;
  - outputs single-part LineStrings between nodes, preserving geometry and attributes.
- Project skill `qgis4-plugin-dev` documenting QGIS 4 / Qt6 plugin conventions.
- Windows deploy/package PowerShell scripts, dev docs, and a pytest suite.
