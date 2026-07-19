# -*- coding: utf-8 -*-
"""The ``Topology split`` Processing algorithm.

Takes a **single line layer** and rebuilds its topology *against itself*:

1. Works on a line (polyline) layer.
2. Splits where the **end of a line touches another line** (T-junctions).
3. Preserves the original geometry of the lines (no vertices are moved or dropped).
4. If a line's dangling end comes **within a configurable tolerance** of another
   line, the end is **extended along its own direction** until it meets that line.
5. Splits **both** lines at every crossing (X-intersections) too.
6. Output features are **single-part** ``LineString`` s (never ``MultiLineString``);
   each runs from one node to the next, keeping the shape in between.
7. Attributes are inherited by every resulting part.

QGIS 4.0 notes
--------------
* Import through ``qgis.core`` / ``qgis.PyQt`` (Qt6 / PyQt6 backend).
* Fully-scoped enums: ``Qgis.WkbType.LineString``, ``Qgis.GeometryType.Line``,
  ``QgsProcessing.SourceType.TypeVectorLine``, ``QgsFeatureSink.Flag.FastInsert``.

Pipeline: explode to single-part lines → extend dangles (step 4) → collect node
points (steps 2 & 5) → cut each line at its nodes (step 6) → write parts (step 7).

Known limitations (documented, not silent): geometry is treated as planar 2D — Z/M
values are dropped; long collinear overlaps are noded only at their extremities;
the dangle-extension pass is single-pass (extensions are matched against the input
geometry, not against other lines' fresh extensions).
"""

import math

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureSink,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsRectangle,
    QgsSpatialIndex,
)


# --------------------------------------------------------------------------- #
# Small planar-geometry helpers (operate on lists of QgsPointXY).
# --------------------------------------------------------------------------- #
def _dist(a, b):
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def _polyline_length(pts):
    return sum(_dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def _extract_points(geom):
    """Flatten any intersection result into a list of QgsPointXY.

    Handles Point / MultiPoint, and (for collinear overlaps) the endpoints of any
    Line part, recursing through GeometryCollections.
    """
    points = []
    if geom is None or geom.isEmpty():
        return points

    gtype = geom.type()
    if gtype == Qgis.GeometryType.Point:
        if geom.isMultipart():
            points.extend(geom.asMultiPoint())
        else:
            points.append(geom.asPoint())
    elif gtype == Qgis.GeometryType.Line:
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
    """Split a polyline (list of QgsPointXY) at the given distances-along-line.

    Distances at (or beyond) the endpoints are ignored. Cut points that fall on an
    existing vertex reuse that vertex; cut points inside a segment are inserted.
    Returns a list of vertex-lists, each a single-part polyline sharing nodes with
    its neighbours. Original vertices are preserved exactly.
    """
    if len(vertices) < 2:
        return [vertices] if len(vertices) == 2 else []

    cum = [0.0]
    for i in range(1, len(vertices)):
        cum.append(cum[-1] + _dist(vertices[i - 1], vertices[i]))
    total = cum[-1]

    cuts = sorted(d for d in cut_distances if eps < d < total - eps)

    # Build an augmented vertex list, flagging which points are cut nodes.
    aug = []  # (QgsPointXY, is_cut)
    ci = 0
    for k in range(len(vertices)):
        if k > 0:
            # Insert cut points that lie strictly inside segment (k-1, k).
            while ci < len(cuts) and cuts[ci] < cum[k] - eps:
                d = cuts[ci]
                if d > cum[k - 1] + eps:
                    seg_len = cum[k] - cum[k - 1]
                    t = (d - cum[k - 1]) / seg_len if seg_len > 0 else 0.0
                    px = vertices[k - 1].x() + t * (vertices[k].x() - vertices[k - 1].x())
                    py = vertices[k - 1].y() + t * (vertices[k].y() - vertices[k - 1].y())
                    aug.append((QgsPointXY(px, py), True))
                ci += 1
        # A cut coincident with this vertex just flags it as a node.
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


class TopologySplitAlgorithm(QgsProcessingAlgorithm):
    """Self-node a line layer: extend dangles, split at all nodes, inherit attrs."""

    INPUT = "INPUT"
    TOLERANCE = "TOLERANCE"
    OUTPUT = "OUTPUT"

    # --- boilerplate -------------------------------------------------------
    def tr(self, string):
        return QCoreApplication.translate("TopologySplitAlgorithm", string)

    def createInstance(self):
        return TopologySplitAlgorithm()

    def name(self):
        return "topologysplit"

    def displayName(self):
        return self.tr("Topology split")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Rebuilds line topology on a single line layer.\n\n"
            "<b>What it does</b>\n"
            "• Splits both lines at every crossing (X) and where one line's end "
            "touches another line (T).\n"
            "• Optionally extends a dangling line end, along its own direction, up "
            "to the <b>Snap/extend tolerance</b>, until it meets another line — then "
            "splits there too.\n"
            "• Output features are single-part LineStrings running node-to-node; the "
            "shape between nodes and all attributes are preserved.\n\n"
            "<b>Snap/extend tolerance</b> is in the layer's map units. Set it to 0 to "
            "disable extension and only node existing intersections."
        )

    # --- parameters --------------------------------------------------------
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input line layer"),
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        tolerance = QgsProcessingParameterDistance(
            self.TOLERANCE,
            self.tr("Snap/extend tolerance (0 = no extension)"),
            defaultValue=0.0,
            parentParameterName=self.INPUT,
        )
        tolerance.setMinimum(0.0)
        self.addParameter(tolerance)
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Noded lines"),
            )
        )

    # --- execution ---------------------------------------------------------
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            source.fields(),
            Qgis.WkbType.LineString,  # always single-part 2D lines
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Planar epsilon scaled to the data extent (units = CRS units).
        extent = source.sourceExtent()
        diag = math.hypot(extent.width(), extent.height()) if not extent.isEmpty() else 1.0
        eps = max(diag * 1e-9, 1e-9)

        # --- step 0: explode to single-part polylines -----------------------
        # lines[i] = {"pts": [QgsPointXY,...], "attrs": [...]}
        lines = []
        for feat in source.getFeatures():
            if feedback.isCanceled():
                return {self.OUTPUT: dest_id}
            geom = feat.geometry()
            if geom.isEmpty():
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
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        geoms = [QgsGeometry.fromPolylineXY(line["pts"]) for line in lines]
        index = QgsSpatialIndex()
        for i, geom in enumerate(geoms):
            f = QgsFeature(i)
            f.setGeometry(geom)
            index.addFeature(f)

        # --- step 4 (run first): extend dangling ends -----------------------
        extended = 0
        if tolerance > 0:
            feedback.pushInfo(self.tr("Extending dangling ends…"))
            for i, line in enumerate(lines):
                if feedback.isCanceled():
                    return {self.OUTPUT: dest_id}
                for at_start in (True, False):
                    new_pt = self._extend_end(i, line["pts"], at_start, geoms, index, tolerance, eps)
                    if new_pt is not None:
                        if at_start:
                            line["pts"].insert(0, new_pt)
                        else:
                            line["pts"].append(new_pt)
                        extended += 1
                feedback.setProgress(int(i / len(lines) * 40))
            # Rebuild geometries/index with the extended ends.
            geoms = [QgsGeometry.fromPolylineXY(line["pts"]) for line in lines]
            index = QgsSpatialIndex()
            for i, geom in enumerate(geoms):
                f = QgsFeature(i)
                f.setGeometry(geom)
                index.addFeature(f)

        # --- steps 2 & 5: collect node points per line ----------------------
        feedback.pushInfo(self.tr("Computing intersections…"))
        cut_points = [[] for _ in lines]  # cut_points[i] = [QgsPointXY,...]
        for i, geom_i in enumerate(geoms):
            if feedback.isCanceled():
                return {self.OUTPUT: dest_id}
            for j in index.intersects(geom_i.boundingBox()):
                if j <= i:
                    continue
                inter = geom_i.intersection(geoms[j])
                pts = _extract_points(inter)
                if pts:
                    cut_points[i].extend(pts)
                    cut_points[j].extend(pts)
            feedback.setProgress(40 + int(i / len(lines) * 40))

        # --- step 6 & 3 & 7: cut each line at its nodes, write parts ---------
        feedback.pushInfo(self.tr("Splitting lines at nodes…"))
        n_out = 0
        for i, line in enumerate(lines):
            if feedback.isCanceled():
                break
            pts = line["pts"]
            geom_i = geoms[i]
            length = geom_i.length()

            # Convert node points to distances-along-line (only those on the line).
            cut_dists = []
            for p in cut_points[i]:
                pgeom = QgsGeometry.fromPointXY(p)
                if geom_i.distance(pgeom) > eps:
                    continue
                d = geom_i.lineLocatePoint(pgeom)
                if 0.0 <= d <= length:
                    cut_dists.append(d)

            for part_pts in _split_polyline(pts, cut_dists, eps):
                out = QgsFeature(source.fields())
                out.setAttributes(line["attrs"])
                out.setGeometry(QgsGeometry.fromPolylineXY(part_pts))
                sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
                n_out += 1
            feedback.setProgress(80 + int(i / len(lines) * 20))

        feedback.pushInfo(
            self.tr("Done: {parts} parts from {inputs} lines, {ext} ends extended.").format(
                parts=n_out, inputs=len(lines), ext=extended
            )
        )
        return {self.OUTPUT: dest_id}

    # --- helpers -----------------------------------------------------------
    def _extend_end(self, i, pts, at_start, geoms, index, tolerance, eps):
        """Return the extension point for a dangling end, or None.

        A dangle is an endpoint that does not already lie on another line. It is
        extended straight along the direction of its last segment; if that ray
        meets another line within ``tolerance``, the meeting point is returned.
        """
        if at_start:
            end = pts[0]
            neighbor = pts[1]
        else:
            end = pts[-1]
            neighbor = pts[-2]

        end_geom = QgsGeometry.fromPointXY(end)

        # Already touching another line? Then it is not a dangle.
        probe = QgsRectangle(end.x() - eps, end.y() - eps, end.x() + eps, end.y() + eps)
        for j in index.intersects(probe):
            if j != i and geoms[j].distance(end_geom) <= eps:
                return None

        # Outward unit direction = along the last segment, pointing away from the line.
        dx = end.x() - neighbor.x()
        dy = end.y() - neighbor.y()
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
