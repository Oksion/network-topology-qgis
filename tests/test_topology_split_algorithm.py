# -*- coding: utf-8 -*-
"""Functional tests for the Topology split algorithm.

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


def _memory_layer(wkb, name, wkt_geoms):
    layer = QgsVectorLayer(f"{wkb}?crs=EPSG:3857&field=id:integer", name, "memory")
    provider = layer.dataProvider()
    feats = []
    for i, wkt in enumerate(wkt_geoms):
        f = QgsFeature(layer.fields())
        f.setAttributes([i])
        f.setGeometry(QgsGeometry.fromWkt(wkt))
        feats.append(f)
    provider.addFeatures(feats)
    layer.updateExtents()
    return layer


def test_polygon_split_into_two_parts(qgis_app):
    # A 10x10 square...
    square = "Polygon ((0 0, 10 0, 10 10, 0 10, 0 0))"
    inp = _memory_layer("Polygon", "input", [square])
    # ...cut by a vertical line crossing it edge-to-edge.
    cut = _memory_layer("LineString", "cut", ["LineString (5 -1, 5 11)"])

    alg = TopologySplitAlgorithm()
    alg.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    params = {
        "INPUT": inp,
        "SPLIT_LAYER": cut,
        "OUTPUT": "memory:",
    }
    results = alg.run(params, context, feedback)[0]

    out = context.getMapLayer(results["OUTPUT"])
    assert out is not None
    assert out.featureCount() == 2, "square should be split into two parts"

    # Attributes preserved, areas sum back to the original 100.
    areas = [f.geometry().area() for f in out.getFeatures()]
    assert abs(sum(areas) - 100.0) < 1e-6
    assert all(f["id"] == 0 for f in out.getFeatures())


def test_no_crossing_line_leaves_feature_intact(qgis_app):
    square = "Polygon ((0 0, 10 0, 10 10, 0 10, 0 0))"
    inp = _memory_layer("Polygon", "input", [square])
    # A line that does not cross the square.
    cut = _memory_layer("LineString", "cut", ["LineString (20 20, 30 30)"])

    alg = TopologySplitAlgorithm()
    alg.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()

    results = alg.run(
        {"INPUT": inp, "SPLIT_LAYER": cut, "OUTPUT": "memory:"},
        context,
        feedback,
    )[0]

    out = context.getMapLayer(results["OUTPUT"])
    assert out.featureCount() == 1
