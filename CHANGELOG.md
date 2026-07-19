# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
### Added
- **Resolve dangles** algorithm (`topology_split:resolvedangles`): directionally
  extend undershooting dangles and trim overshooting ones, under one tolerance with
  independent toggles; one output feature per input feature.
- **Collapse pseudo-nodes** algorithm (`topology_split:collapsepseudonodes`): merge
  chains of lines through degree-2 nodes into single lines, with an optional
  attribute-group barrier; attributes inherited from the longest segment.
- Shared helpers extracted into `topology_utils.py`.
- pytest suites for both new algorithms (green on QGIS 4.2).

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
