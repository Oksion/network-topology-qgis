# -*- coding: utf-8 -*-
"""Functional tests for the Topology split (self-noding) algorithm.

Skipped automatically when PyQGIS is unavailable (see conftest.py).
"""

import pytest

pytest.importorskip("qgis.core", reason="PyQGIS (qgis) not importable")

from qgis.core import (  # noqa: E402
    QgsFeature,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorLayer,
)

from topology_split_algorithm import TopologySplitAlgorithm  # noqa: E402


def _line_layer(wkt_geoms, name="lines"):
    layer = QgsVectorLayer(
        "LineString?crs=EPSG:3857&field=id:integer&field=note:string", name, "memory"
    )
    provider = layer.dataProvider()
    feats = []
    for i, wkt in enumerate(wkt_geoms):
        f = QgsFeature(layer.fields())
        f.setAttributes([i, f"line-{i}"])
        f.setGeometry(QgsGeometry.fromWkt(wkt))
        feats.append(f)
    provider.addFeatures(feats)
    layer.updateExtents()
    return layer


def _run(layer, tolerance=0.0):
    alg = TopologySplitAlgorithm()
    alg.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    results = alg.run(
        {"INPUT": layer, "TOLERANCE": tolerance, "OUTPUT": "memory:"},
        context,
        feedback,
    )[0]
    return context.getMapLayer(results["OUTPUT"])


def _total_length(layer):
    return sum(f.geometry().length() for f in layer.getFeatures())


def test_x_crossing_splits_both_lines(qgis_app):
    # Two lines crossing at (5,5) -> 4 parts, both lines split.
    out = _run(
        _line_layer(
            [
                "LineString (0 5, 10 5)",
                "LineString (5 0, 5 10)",
            ]
        )
    )
    assert out.featureCount() == 4
    # Geometry preserved: total length unchanged (2 * 10).
    assert abs(_total_length(out) - 20.0) < 1e-6
    # No multipart output.
    assert all(not f.geometry().isMultipart() for f in out.getFeatures())


def test_t_touch_splits_only_the_touched_line(qgis_app):
    # Line B's end touches the middle of line A -> A splits (2), B stays (1) = 3.
    out = _run(
        _line_layer(
            [
                "LineString (0 0, 10 0)",   # A (touched)
                "LineString (5 0, 5 5)",    # B ends on A at (5,0)
            ]
        )
    )
    assert out.featureCount() == 3
    assert abs(_total_length(out) - 15.0) < 1e-6


def test_attributes_inherited(qgis_app):
    out = _run(
        _line_layer(
            [
                "LineString (0 5, 10 5)",
                "LineString (5 0, 5 10)",
            ]
        )
    )
    # Every part of line 0 keeps note "line-0", every part of line 1 keeps "line-1".
    notes = {f["id"]: f["note"] for f in out.getFeatures()}
    assert notes == {0: "line-0", 1: "line-1"}


def test_dangle_extended_to_reach_other_line(qgis_app):
    # A points at B but stops 0.4 short. With tolerance 1.0 it extends to x=5 and
    # splits B; without tolerance nothing happens.
    lines = [
        "LineString (0 5, 4.6 5)",   # A: dangling end at (4.6, 5), heading +x
        "LineString (5 0, 5 10)",    # B: vertical wall at x=5
    ]

    out_no = _run(_line_layer(lines), tolerance=0.0)
    assert out_no.featureCount() == 2  # untouched: A + B

    out_yes = _run(_line_layer(lines), tolerance=1.0)
    # A now reaches (5,5) -> B is split into two -> A(1) + B(2) = 3.
    assert out_yes.featureCount() == 3
    # A was extended from length 4.6 to 5.0; total grew by ~0.4.
    assert abs(_total_length(out_yes) - (5.0 + 10.0)) < 1e-6


def test_multipart_is_exploded(qgis_app):
    layer = QgsVectorLayer(
        "MultiLineString?crs=EPSG:3857&field=id:integer&field=note:string",
        "multi",
        "memory",
    )
    f = QgsFeature(layer.fields())
    f.setAttributes([0, "line-0"])
    f.setGeometry(
        QgsGeometry.fromWkt("MultiLineString ((0 0, 1 0), (2 0, 3 0))")
    )
    layer.dataProvider().addFeatures([f])
    layer.updateExtents()

    out = _run(layer)
    assert out.featureCount() == 2
    assert all(not g.geometry().isMultipart() for g in out.getFeatures())
    assert all(g["note"] == "line-0" for g in out.getFeatures())
