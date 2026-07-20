# -*- coding: utf-8 -*-
"""Functional tests for the Cluster extents (hull/bbox) algorithm.

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
    QgsWkbTypes,
)

from cluster_hulls_algorithm import ClusterHullsAlgorithm  # noqa: E402


def _layer(wkts):
    layer = QgsVectorLayer("LineString?crs=EPSG:3857&field=id:integer", "lines", "memory")
    feats = []
    for i, w in enumerate(wkts):
        f = QgsFeature(layer.fields())
        f.setAttributes([i])
        f.setGeometry(QgsGeometry.fromWkt(w))
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    return layer


def _run(layer, method=0):
    alg = ClusterHullsAlgorithm()
    alg.initAlgorithm()
    ctx = QgsProcessingContext()
    res = alg.run(
        {"INPUT": layer, "METHOD": method, "OUTPUT": "memory:"},
        ctx,
        QgsProcessingFeedback(),
    )[0]
    return ctx, ctx.getMapLayer(res["OUTPUT"])


BIG = ["LineString (0 0, 10 0)", "LineString (10 0, 10 10)", "LineString (0 0, 0 10)"]
SMALL = [
    "LineString (100 100, 102 100)",
    "LineString (102 100, 101 102)",
    "LineString (101 102, 100 100)",
]


def test_one_polygon_per_cluster_ordered_by_size(qgis_app):
    ctx, out = _run(_layer(BIG + SMALL), method=0)
    assert out.featureCount() == 2
    rows = {f["cluster_id"]: (f["edge_count"], f["length"], f.geometry().area())
            for f in out.getFeatures()}
    # All polygons
    assert all(f.geometry().type() == QgsWkbTypes.GeometryType.PolygonGeometry
               for f in out.getFeatures())
    assert rows[1][0] == 3                       # 3 edges
    assert abs(rows[1][1] - 30.0) < 1e-6         # total length
    assert rows[1][2] > rows[2][2]               # cluster 1 is the larger area


def test_bounding_box_method(qgis_app):
    ctx, out = _run(_layer(BIG), method=1)
    f = next(out.getFeatures())
    assert abs(f.geometry().area() - 100.0) < 1e-6


def test_oriented_bbox_method(qgis_app):
    ctx, out = _run(_layer(BIG), method=2)
    assert next(out.getFeatures()).geometry().area() > 0


def test_degenerate_line_still_polygon(qgis_app):
    ctx, out = _run(_layer(["LineString (0 0, 5 5)"]), method=0)
    f = next(out.getFeatures())
    assert f.geometry().type() == QgsWkbTypes.GeometryType.PolygonGeometry
    assert f.geometry().area() > 0  # diagonal → bbox fallback has area
