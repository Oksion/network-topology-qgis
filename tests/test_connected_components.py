# -*- coding: utf-8 -*-
"""Functional tests for the Connected components algorithm.

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

from connected_components_algorithm import ConnectedComponentsAlgorithm  # noqa: E402


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
    alg = ConnectedComponentsAlgorithm()
    alg.initAlgorithm()
    ctx = QgsProcessingContext()
    res = alg.run({"INPUT": layer, "OUTPUT": "memory:"}, ctx, QgsProcessingFeedback())[0]
    return ctx, ctx.getMapLayer(res["OUTPUT"])


def _clusters(out):
    return {f["id"]: (f["cluster_id"], f["cluster_size"]) for f in out.getFeatures()}


def test_disjoint_lines_are_two_clusters(qgis_app):
    ctx, out = _run(_layer(["LineString (0 0, 1 0)", "LineString (5 5, 6 5)"]))
    c = _clusters(out)
    assert c[0][0] != c[1][0]
    assert c[0][1] == 1 and c[1][1] == 1


def test_connected_lines_share_cluster(qgis_app):
    ctx, out = _run(_layer(["LineString (0 0, 5 0)", "LineString (5 0, 10 0)"]))
    c = _clusters(out)
    assert c[0][0] == c[1][0]
    assert c[0][1] == 2


def test_ids_ordered_by_size(qgis_app):
    ctx, out = _run(
        _layer(
            [
                "LineString (0 0, 1 0)",
                "LineString (1 0, 2 0)",
                "LineString (2 0, 3 0)",  # chain of 3
                "LineString (10 10, 11 10)",  # stray
            ]
        )
    )
    c = _clusters(out)
    assert c[0][0] == 1 and c[0][1] == 3  # largest → cluster 1
    assert c[3][0] == 2 and c[3][1] == 1  # stray → cluster 2


def test_field_name_collision(qgis_app):
    layer = QgsVectorLayer(
        "LineString?crs=EPSG:3857&field=cluster_id:string", "lines", "memory"
    )
    f = QgsFeature(layer.fields())
    f.setAttributes(["x"])
    f.setGeometry(QgsGeometry.fromWkt("LineString (0 0, 1 0)"))
    layer.dataProvider().addFeatures([f])
    layer.updateExtents()

    ctx, out = _run(layer)
    names = [fld.name() for fld in out.fields()]
    assert "cluster_id" in names and "cluster_id_2" in names
