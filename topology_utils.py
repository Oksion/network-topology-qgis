# -*- coding: utf-8 -*-
"""Shared geometry helpers for the Network Topology toolkit.

Pure, module-level functions operating mostly on lists of ``QgsPointXY`` so they
stay unit-testable. Imported by every algorithm in the provider.

QGIS 4.0 notes: import through ``qgis.core`` / ``qgis.PyQt`` (Qt6 / PyQt6); use
fully-scoped enums at the call sites.
"""

import math

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsSpatialIndex,
)


def dist(a, b):
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def polyline_length(pts):
    return sum(dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def data_eps(extent):
    """A planar epsilon scaled to the data extent (in CRS units)."""
    diag = math.hypot(extent.width(), extent.height()) if not extent.isEmpty() else 1.0
    return max(diag * 1e-9, 1e-9)


def explode(geometry):
    """Return a list of single-part polylines (each a list of QgsPointXY)."""
    if geometry is None or geometry.isEmpty():
        return []
    if geometry.isMultipart():
        return [list(part) for part in geometry.asMultiPolyline() if len(part) >= 2]
    polyline = geometry.asPolyline()
    return [list(polyline)] if len(polyline) >= 2 else []


def build_line_index(geoms):
    """QgsSpatialIndex over a list of geometries, feature id == list position."""
    index = QgsSpatialIndex()
    for i, geom in enumerate(geoms):
        f = QgsFeature(i)
        f.setGeometry(geom)
        index.addFeature(f)
    return index


def extract_points(geom):
    """Flatten any intersection result into a list of QgsPointXY.

    Handles Point / MultiPoint, and (for collinear overlaps) the endpoints of any
    Line part, recursing through GeometryCollections.
    """
    points = []
    if geom is None or geom.isEmpty():
        return points
    gtype = int(geom.type())  # 0 = Point, 1 = Line, 2 = Polygon
    if gtype == 0:
        if geom.isMultipart():
            points.extend(geom.asMultiPoint())
        else:
            points.append(geom.asPoint())
    elif gtype == 1:
        if geom.isMultipart():
            for part in geom.asMultiPolyline():
                if part:
                    points.append(part[0])
                    points.append(part[-1])
        else:
            polyline = geom.asPolyline()
            if polyline:
                points.append(polyline[0])
                points.append(polyline[-1])
    else:
        for sub in geom.asGeometryCollection():
            points.extend(extract_points(sub))
    return points


def is_dangle(end_pt, i, geoms, index, eps):
    """True if ``end_pt`` (an endpoint of line ``i``) touches no other line."""
    eg = QgsGeometry.fromPointXY(end_pt)
    probe = QgsRectangle(end_pt.x() - eps, end_pt.y() - eps,
                         end_pt.x() + eps, end_pt.y() + eps)
    for j in index.intersects(probe):
        if j != i and geoms[j].distance(eg) <= eps:
            return False
    return True


def extend_end(i, pts, at_start, geoms, index, tolerance, eps):
    """Return the extension point for a dangling end, or None.

    A dangle is extended straight along its last segment; if that ray meets another
    line within ``tolerance``, the nearest meeting point is returned.
    """
    if at_start:
        end, neighbor = pts[0], pts[1]
    else:
        end, neighbor = pts[-1], pts[-2]

    if not is_dangle(end, i, geoms, index, eps):
        return None

    dx, dy = end.x() - neighbor.x(), end.y() - neighbor.y()
    norm = math.hypot(dx, dy)
    if norm <= eps:
        return None
    dx, dy = dx / norm, dy / norm

    far = QgsPointXY(end.x() + dx * tolerance, end.y() + dy * tolerance)
    ray = QgsGeometry.fromPolylineXY([end, far])

    best = None
    for j in index.intersects(ray.boundingBox()):
        if j == i:
            continue
        for x in extract_points(ray.intersection(geoms[j])):
            d = dist(end, x)
            if eps < d <= tolerance + eps and (best is None or d < best[0]):
                best = (d, x)
    return best[1] if best is not None else None


def split_polyline(vertices, cut_distances, eps):
    """Split a polyline at the given distances-along-line, preserving vertices.

    Distances at/beyond the endpoints are ignored. Returns a list of vertex-lists,
    each a single-part polyline sharing nodes with its neighbours.
    """
    if len(vertices) < 2:
        return []

    cum = [0.0]
    for i in range(1, len(vertices)):
        cum.append(cum[-1] + dist(vertices[i - 1], vertices[i]))
    total = cum[-1]

    cuts = sorted(d for d in cut_distances if eps < d < total - eps)

    aug = []  # (QgsPointXY, is_cut)
    ci = 0
    for k in range(len(vertices)):
        if k > 0:
            while ci < len(cuts) and cuts[ci] < cum[k] - eps:
                d = cuts[ci]
                if d > cum[k - 1] + eps:
                    seg_len = cum[k] - cum[k - 1]
                    t = (d - cum[k - 1]) / seg_len if seg_len > 0 else 0.0
                    px = vertices[k - 1].x() + t * (vertices[k].x() - vertices[k - 1].x())
                    py = vertices[k - 1].y() + t * (vertices[k].y() - vertices[k - 1].y())
                    aug.append((QgsPointXY(px, py), True))
                ci += 1
        is_cut = False
        while ci < len(cuts) and abs(cuts[ci] - cum[k]) <= eps:
            is_cut = True
            ci += 1
        aug.append((vertices[k], is_cut))

    parts = []
    current = [aug[0][0]]
    for idx in range(1, len(aug)):
        point, is_cut = aug[idx]
        current.append(point)
        if is_cut and idx != len(aug) - 1:
            parts.append(current)
            current = [point]
    if len(current) >= 2:
        parts.append(current)

    return [p for p in parts if len(p) >= 2 and polyline_length(p) > eps]


def sub_polyline(vertices, d0, d1, eps):
    """Return the sub-polyline of ``vertices`` between distances d0..d1 along it.

    Interior vertices are preserved; the ends are interpolated at d0 and d1.
    Returns [] if the span is degenerate.
    """
    if len(vertices) < 2:
        return []
    cum = [0.0]
    for i in range(1, len(vertices)):
        cum.append(cum[-1] + dist(vertices[i - 1], vertices[i]))
    total = cum[-1]

    d0 = max(0.0, min(d0, total))
    d1 = max(0.0, min(d1, total))
    if d1 - d0 <= eps:
        return []

    def point_at(d):
        if d <= 0:
            return QgsPointXY(vertices[0])
        if d >= total:
            return QgsPointXY(vertices[-1])
        for k in range(1, len(vertices)):
            if cum[k] >= d:
                seg = cum[k] - cum[k - 1]
                t = (d - cum[k - 1]) / seg if seg > 0 else 0.0
                return QgsPointXY(
                    vertices[k - 1].x() + t * (vertices[k].x() - vertices[k - 1].x()),
                    vertices[k - 1].y() + t * (vertices[k].y() - vertices[k - 1].y()),
                )
        return QgsPointXY(vertices[-1])

    result = [point_at(d0)]
    for k in range(len(vertices)):
        if d0 + eps < cum[k] < d1 - eps:
            result.append(vertices[k])
    result.append(point_at(d1))

    # drop consecutive duplicates
    cleaned = [result[0]]
    for p in result[1:]:
        if dist(p, cleaned[-1]) > eps:
            cleaned.append(p)
    return cleaned if len(cleaned) >= 2 else []
