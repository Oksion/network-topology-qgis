# -*- coding: utf-8 -*-
# =============================================================================
#  Topology Split — standalone script for the QGIS Python Console
# =============================================================================
#  Self-nodes a SINGLE line layer against itself (no plugin install required):
#    * splits both lines at every crossing (X) and endpoint-touch (T);
#    * optionally extends a dangling end along its own direction, up to a
#      tolerance, until it reaches another line — then splits there too;
#    * outputs single-part LineStrings between nodes;
#    * preserves the original geometry and inherits all attributes.
#
#  HOW TO USE
#  ----------
#  1. Open QGIS, load your line layer, select it in the Layers panel.
#  2. Open the Python Console:  Plugins ▸ Python Console  (Ctrl+Alt+P).
#  3. Paste this whole file and press Enter.
#     The result is added to the project as a memory layer "Noded lines".
#
#  Tweak the CONFIG block below (tolerance, which layer, selection-only, …).
#  Requires QGIS 4.0+ (Qt6 / PyQt6).
# =============================================================================

import math

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorLayer,
)
from qgis.utils import iface

# ------------------------------- CONFIG -------------------------------------
# Snap/extend tolerance in the LAYER'S MAP UNITS. 0 = do not extend dangles,
# only node existing intersections.
TOLERANCE = 0.0

# Which layer to process:
#   None  -> the active (selected) layer in the Layers panel
#   "name" or a layer object -> that specific layer
INPUT_LAYER = None

# Process only the selected features of the input layer?
USE_SELECTED_ONLY = False

# Name of the result layer added to the project.
OUTPUT_NAME = "Noded lines"
# ----------------------------------------------------------------------------


# ---- planar-geometry helpers (operate on lists of QgsPointXY) --------------
def _dist(a, b):
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def _polyline_length(pts):
    return sum(_dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def _extract_points(geom):
    """Flatten any intersection result into a list of QgsPointXY."""
    points = []
    if geom is None or geom.isEmpty():
        return points
    gtype = geom.type()  # Qgis.GeometryType
    if int(gtype) == 0:  # Point
        if geom.isMultipart():
            points.extend(geom.asMultiPoint())
        else:
            points.append(geom.asPoint())
    elif int(gtype) == 1:  # Line
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
            points.extend(_extract_points(sub))
    return points


def _split_polyline(vertices, cut_distances, eps):
    """Split a polyline at the given distances-along-line, preserving vertices."""
    if len(vertices) < 2:
        return []

    cum = [0.0]
    for i in range(1, len(vertices)):
        cum.append(cum[-1] + _dist(vertices[i - 1], vertices[i]))
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

    return [p for p in parts if len(p) >= 2 and _polyline_length(p) > eps]


def _extend_end(i, pts, at_start, geoms, index, tolerance, eps):
    """Return the extension point for a dangling end, or None."""
    if at_start:
        end, neighbor = pts[0], pts[1]
    else:
        end, neighbor = pts[-1], pts[-2]

    end_geom = QgsGeometry.fromPointXY(end)
    probe = QgsRectangle(end.x() - eps, end.y() - eps, end.x() + eps, end.y() + eps)
    for j in index.intersects(probe):
        if j != i and geoms[j].distance(end_geom) <= eps:
            return None  # already touching another line — not a dangle

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
        for x in _extract_points(ray.intersection(geoms[j])):
            d = _dist(end, x)
            if eps < d <= tolerance + eps and (best is None or d < best[0]):
                best = (d, x)
    return best[1] if best is not None else None


# ---- core: build the noded memory layer ------------------------------------
def run_topology_split(layer, tolerance=0.0, output_name="Noded lines",
                       selected_only=False):
    """Run the self-noding on `layer` and return a new in-memory line layer."""
    if layer is None:
        raise ValueError("No input layer.")

    fields = layer.fields()
    feats_iter = layer.getSelectedFeatures() if selected_only else layer.getFeatures()

    # step 0: explode to single-part polylines, keep attributes
    lines = []
    for feat in feats_iter:
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        attrs = feat.attributes()
        if geom.isMultipart():
            for part in geom.asMultiPolyline():
                if len(part) >= 2:
                    lines.append({"pts": list(part), "attrs": attrs})
        else:
            polyline = geom.asPolyline()
            if len(polyline) >= 2:
                lines.append({"pts": list(polyline), "attrs": attrs})

    if not lines:
        raise ValueError("Input has no usable line geometries "
                         "(is it a line layer? is anything selected?).")

    ext = layer.extent()
    diag = math.hypot(ext.width(), ext.height()) if not ext.isEmpty() else 1.0
    eps = max(diag * 1e-9, 1e-9)

    def _rebuild():
        gs = [QgsGeometry.fromPolylineXY(ln["pts"]) for ln in lines]
        idx = QgsSpatialIndex()
        for i, g in enumerate(gs):
            f = QgsFeature(i)
            f.setGeometry(g)
            idx.addFeature(f)
        return gs, idx

    geoms, index = _rebuild()

    # step 4: extend dangling ends
    extended = 0
    if tolerance > 0:
        for i, line in enumerate(lines):
            for at_start in (True, False):
                p = _extend_end(i, line["pts"], at_start, geoms, index, tolerance, eps)
                if p is not None:
                    line["pts"].insert(0, p) if at_start else line["pts"].append(p)
                    extended += 1
        geoms, index = _rebuild()

    # steps 2 & 5: collect node points per line
    cut_points = [[] for _ in lines]
    for i, geom_i in enumerate(geoms):
        for j in index.intersects(geom_i.boundingBox()):
            if j <= i:
                continue
            pts = _extract_points(geom_i.intersection(geoms[j]))
            if pts:
                cut_points[i].extend(pts)
                cut_points[j].extend(pts)

    # build output memory layer (single-part LineString, same fields + CRS)
    crs = layer.crs()
    uri = "LineString?crs=" + (crs.authid() or "EPSG:4326")
    out = QgsVectorLayer(uri, output_name, "memory")
    out.setCrs(crs)
    dp = out.dataProvider()
    dp.addAttributes(list(fields))
    out.updateFields()

    # steps 6, 3 & 7: cut each line at its nodes, write single-part parts
    out_feats = []
    for i, line in enumerate(lines):
        geom_i = geoms[i]
        length = geom_i.length()
        cut_dists = []
        for p in cut_points[i]:
            pg = QgsGeometry.fromPointXY(p)
            if geom_i.distance(pg) > eps:
                continue
            d = geom_i.lineLocatePoint(pg)
            if 0.0 <= d <= length:
                cut_dists.append(d)
        for part_pts in _split_polyline(line["pts"], cut_dists, eps):
            f = QgsFeature(out.fields())
            f.setAttributes(line["attrs"])
            f.setGeometry(QgsGeometry.fromPolylineXY(part_pts))
            out_feats.append(f)

    dp.addFeatures(out_feats)
    out.updateExtents()
    print("Topology split: %d parts from %d lines, %d ends extended."
          % (len(out_feats), len(lines), extended))
    return out


def main():
    src = INPUT_LAYER
    if isinstance(src, str):
        found = QgsProject.instance().mapLayersByName(src)
        src = found[0] if found else None
        if src is None:
            print('Layer named "%s" not found.' % INPUT_LAYER)
            return
    if src is None and iface is not None:
        src = iface.activeLayer()
    if src is None:
        print("No input layer. Select a line layer in the Layers panel, "
              "or set INPUT_LAYER at the top of the script.")
        return

    result = run_topology_split(src, TOLERANCE, OUTPUT_NAME, USE_SELECTED_ONLY)
    QgsProject.instance().addMapLayer(result)
    if iface is not None:
        iface.mapCanvas().refresh()
    print('Done. Added layer "%s" to the project.' % OUTPUT_NAME)


# Runs automatically when the whole file is pasted into the QGIS console.
main()
