"""Functional tests for the Network nodes algorithm.

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

from network_nodes_algorithm import NetworkNodesAlgorithm  # noqa: E402


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


def _run(layer):
    alg = NetworkNodesAlgorithm()
    alg.initAlgorithm()
    ctx = QgsProcessingContext()
    res = alg.run({"INPUT": layer, "OUTPUT": "memory:"}, ctx, QgsProcessingFeedback())[0]
    return ctx, ctx.getMapLayer(res["OUTPUT"])


def _by_type(out):
    counts = {"dangle": 0, "pseudo": 0, "junction": 0}
    for f in out.getFeatures():
        counts[f["node_type"]] += 1
    return counts


def test_y_junction(qgis_app):
    ctx, out = _run(
        _layer(
            [
                "LineString (5 0, 0 0)",
                "LineString (5 0, 10 0)",
                "LineString (5 0, 5 5)",
            ]
        )
    )
    assert out.geometryType() == QgsWkbTypes.GeometryType.PointGeometry
    assert out.featureCount() == 4
    t = _by_type(out)
    assert t["dangle"] == 3 and t["junction"] == 1
    center = [f for f in out.getFeatures() if f["node_type"] == "junction"][0]
    assert center["degree"] == 3
    assert all(f["edge_count"] == f["degree"] for f in out.getFeatures())


def test_pseudo_node(qgis_app):
    ctx, out = _run(_layer(["LineString (0 0, 5 0)", "LineString (5 0, 10 0)"]))
    t = _by_type(out)
    assert out.featureCount() == 3
    assert t["dangle"] == 2 and t["pseudo"] == 1


def test_unnoded_crossing_has_no_junction(qgis_app):
    # Two crossing lines whose endpoints don't meet at the crossing → 4 dangles.
    ctx, out = _run(_layer(["LineString (0 5, 10 5)", "LineString (5 0, 5 10)"]))
    t = _by_type(out)
    assert t["dangle"] == 4 and t["junction"] == 0


def test_closed_ring_is_one_pseudo_node(qgis_app):
    ctx, out = _run(_layer(["LineString (0 0, 4 0, 4 4, 0 4, 0 0)"]))
    t = _by_type(out)
    assert out.featureCount() == 1 and t["pseudo"] == 1
