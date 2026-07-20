"""Functional tests for the Collapse pseudo-nodes algorithm.

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

from pseudonode_collapse_algorithm import PseudoNodeCollapseAlgorithm  # noqa: E402


def _layer(rows, with_grp=False):
    fdef = "field=id:integer" + ("&field=grp:string" if with_grp else "")
    layer = QgsVectorLayer("LineString?crs=EPSG:3857&" + fdef, "lines", "memory")
    feats = []
    for i, row in enumerate(rows):
        wkt = row[0]
        f = QgsFeature(layer.fields())
        f.setAttributes([i, row[1]] if with_grp else [i])
        f.setGeometry(QgsGeometry.fromWkt(wkt))
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    return layer


def _run(layer, group_field=""):
    alg = PseudoNodeCollapseAlgorithm()
    alg.initAlgorithm()
    ctx = QgsProcessingContext()
    res = alg.run(
        {"INPUT": layer, "GROUP_FIELD": group_field, "OUTPUT": "memory:"},
        ctx,
        QgsProcessingFeedback(),
    )[0]
    return ctx, ctx.getMapLayer(res["OUTPUT"])


def test_two_collinear_merge(qgis_app):
    ctx, out = _run(_layer([("LineString (0 0, 5 0)",), ("LineString (5 0, 10 0)",)]))
    assert out.featureCount() == 1
    assert abs(next(out.getFeatures()).geometry().length() - 10.0) < 1e-6


def test_degree_three_junction_kept(qgis_app):
    ctx, out = _run(
        _layer(
            [
                ("LineString (0 0, 5 0)",),
                ("LineString (5 0, 10 0)",),
                ("LineString (5 0, 5 5)",),
            ]
        )
    )
    assert out.featureCount() == 3


def test_group_field_barrier(qgis_app):
    rows = [("LineString (0 0, 5 0)", "A"), ("LineString (5 0, 10 0)", "B")]
    ctx, out = _run(_layer(rows, with_grp=True), group_field="grp")
    assert out.featureCount() == 2  # different grp → not merged

    rows_same = [("LineString (0 0, 5 0)", "A"), ("LineString (5 0, 10 0)", "A")]
    ctx, out = _run(_layer(rows_same, with_grp=True), group_field="grp")
    assert out.featureCount() == 1


def test_closed_ring_merges_to_one(qgis_app):
    ring = [
        ("LineString (0 0, 4 0)",),
        ("LineString (4 0, 4 4)",),
        ("LineString (4 4, 0 4)",),
        ("LineString (0 4, 0 0)",),
    ]
    ctx, out = _run(_layer(ring))
    assert out.featureCount() == 1
    assert abs(next(out.getFeatures()).geometry().length() - 16.0) < 1e-6


def test_attributes_from_longest_segment(qgis_app):
    ctx, out = _run(_layer([("LineString (0 0, 2 0)",), ("LineString (2 0, 10 0)",)]))
    assert next(out.getFeatures())["id"] == 1  # longer segment wins
