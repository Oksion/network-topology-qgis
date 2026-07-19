# -*- coding: utf-8 -*-
"""Functional tests for the Resolve dangles algorithm.

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

from dangle_resolver_algorithm import DangleResolverAlgorithm  # noqa: E402


def _layer(wkts):
    layer = QgsVectorLayer(
        "LineString?crs=EPSG:3857&field=id:integer", "lines", "memory"
    )
    feats = []
    for i, w in enumerate(wkts):
        f = QgsFeature(layer.fields())
        f.setAttributes([i])
        f.setGeometry(QgsGeometry.fromWkt(w))
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    return layer


def _run(layer, tolerance, extend, trim):
    alg = DangleResolverAlgorithm()
    alg.initAlgorithm()
    ctx = QgsProcessingContext()
    res = alg.run(
        {
            "INPUT": layer,
            "TOLERANCE": tolerance,
            "FIX_UNDERSHOOTS": extend,
            "FIX_OVERSHOOTS": trim,
            "OUTPUT": "memory:",
        },
        ctx,
        QgsProcessingFeedback(),
    )[0]
    return ctx, ctx.getMapLayer(res["OUTPUT"])


def _len(layer, fid):
    return [f.geometry().length() for f in layer.getFeatures() if f["id"] == fid][0]


def test_undershoot_is_extended(qgis_app):
    lines = ["LineString (0 5, 4.6 5)", "LineString (5 0, 5 10)"]
    ctx, out = _run(_layer(lines), 1.0, True, False)
    assert out.featureCount() == 2  # no splitting, just cleaning
    assert abs(_len(out, 0) - 5.0) < 1e-6  # A grew from 4.6 to 5.0


def test_overshoot_is_trimmed(qgis_app):
    lines = ["LineString (0 5, 6 5)", "LineString (5 0, 5 10)"]  # A overshoots by 1.0
    ctx, out = _run(_layer(lines), 1.5, False, True)
    assert abs(_len(out, 0) - 5.0) < 1e-6  # trimmed back to the crossing


def test_tail_longer_than_tolerance_kept(qgis_app):
    lines = ["LineString (0 5, 6 5)", "LineString (5 0, 5 10)"]
    ctx, out = _run(_layer(lines), 0.5, False, True)
    assert abs(_len(out, 0) - 6.0) < 1e-6  # 1.0 tail > 0.5 tolerance → untouched


def test_connected_end_untouched(qgis_app):
    lines = ["LineString (0 0, 5 0)", "LineString (5 0, 10 0)"]
    ctx, out = _run(_layer(lines), 2.0, True, True)
    total = sum(f.geometry().length() for f in out.getFeatures())
    assert abs(total - 10.0) < 1e-6
