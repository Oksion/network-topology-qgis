# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-07-19
### Added
- Initial scaffold for QGIS 4.0 (Qt6 / PyQt6).
- Processing provider `Topology Split` with the `Topology split` algorithm.
- Splits input polygon/line features by a splitter-lines layer using a spatial
  index; preserves attributes on each resulting part.
- Project skill `qgis4-plugin-dev` documenting QGIS 4 / Qt6 plugin conventions.
- Windows deploy/package PowerShell scripts, dev docs, and a pytest skeleton.
