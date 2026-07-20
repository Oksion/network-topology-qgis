"""The ``Resolve dangles`` Processing algorithm.

Cleans the dangling ends of a line network, keeping the same features (one output
feature per input feature, attributes and multipart structure preserved):

* **Undershoot** — a free end that stops short of another line is *extended along
  its own direction* until it reaches that line (within the tolerance).
* **Overshoot** — a free end that runs past a junction, leaving a short tail, is
  *trimmed back* to that junction (when the tail is shorter than the tolerance).

Both share one ``Tolerance`` (map units) and can be toggled independently. This is
the directional counterpart to core "Extend lines" (which extends blindly) and
GRASS ``v.clean`` (which snaps vertices sideways) — here the geometry is only ever
grown along its own bearing or cut at an existing crossing.

Geometry is treated as planar 2D. The pass is single-pass: ends are matched against
the input network, not against other ends' fresh edits.
"""

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureSink,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication

try:
    from .topology_utils import (
        build_line_index,
        data_eps,
        explode,
        extend_end,
        extract_points,
        is_dangle,
        polyline_length,
        sub_polyline,
    )
except ImportError:
    from topology_utils import (
        build_line_index,
        data_eps,
        explode,
        extend_end,
        extract_points,
        is_dangle,
        polyline_length,
        sub_polyline,
    )


class DangleResolverAlgorithm(QgsProcessingAlgorithm):
    """Extend undershooting dangles and trim overshooting ones."""

    INPUT = "INPUT"
    TOLERANCE = "TOLERANCE"
    FIX_UNDERSHOOTS = "FIX_UNDERSHOOTS"
    FIX_OVERSHOOTS = "FIX_OVERSHOOTS"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("DangleResolverAlgorithm", string)

    def createInstance(self):
        return DangleResolverAlgorithm()

    def name(self):
        return "resolvedangles"

    def displayName(self):
        return self.tr("Resolve dangles (extend / trim)")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Cleans dangling ends of a line network, keeping one output feature per "
            "input feature (attributes preserved).\n\n"
            "<b>Undershoot → extend:</b> a free end that stops short of another line "
            "is extended <i>along its own direction</i> until it reaches that line, "
            "if the gap is within the <b>Tolerance</b>.\n\n"
            "<b>Overshoot → trim:</b> a free end that runs past a crossing, leaving a "
            "tail shorter than the <b>Tolerance</b>, is cut back to that crossing.\n\n"
            "Tolerance is in the layer's map units. This tool does not split lines — "
            "run <i>Topology split</i> afterwards to node the network."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input line layer"),
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        tol = QgsProcessingParameterDistance(
            self.TOLERANCE,
            self.tr("Tolerance (max gap to close / tail to trim)"),
            defaultValue=0.0,
            parentParameterName=self.INPUT,
        )
        tol.setMinimum(0.0)
        self.addParameter(tol)
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FIX_UNDERSHOOTS, self.tr("Extend undershoots"), defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FIX_OVERSHOOTS, self.tr("Trim overshoots"), defaultValue=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Resolved lines"))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
        do_extend = self.parameterAsBool(parameters, self.FIX_UNDERSHOOTS, context)
        do_trim = self.parameterAsBool(parameters, self.FIX_OVERSHOOTS, context)

        is_multi = QgsWkbTypes.isMultiType(source.wkbType())
        out_wkb = Qgis.WkbType.MultiLineString if is_multi else Qgis.WkbType.LineString
        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            source.fields(),
            out_wkb,
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())

        # Flatten every part of every feature; keep a back-reference to rebuild.
        features = []  # {"attrs": [...], "parts": [pts, ...]}
        flat_pts, flat_ref = [], []
        for feat in source.getFeatures():
            parts = explode(feat.geometry())
            fi = len(features)
            features.append({"attrs": feat.attributes(), "parts": parts})
            for li, pts in enumerate(parts):
                flat_pts.append(pts)
                flat_ref.append((fi, li))

        if not flat_pts:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        geoms = [QgsGeometry.fromPolylineXY(p) for p in flat_pts]
        index = build_line_index(geoms)

        n_ext = n_trim = 0
        total = len(flat_pts)
        for i, pts in enumerate(flat_pts):
            if feedback.isCanceled():
                break
            geom_i = geoms[i]
            length = geom_i.length()

            trimmed_start = trimmed_end = False
            d0, d1 = 0.0, length

            if do_trim and tolerance > 0:
                junction_ds = self._junction_distances(i, geom_i, geoms, index, eps)
                if is_dangle(pts[0], i, geoms, index, eps):
                    cand = [d for d in junction_ds if eps < d <= tolerance + eps]
                    if cand:
                        d0 = min(cand)
                        trimmed_start = True
                if is_dangle(pts[-1], i, geoms, index, eps):
                    lo = length - tolerance - eps
                    cand = [d for d in junction_ds if lo <= d < length - eps]
                    if cand:
                        d1 = max(cand)
                        trimmed_end = True

            work = pts
            if trimmed_start or trimmed_end:
                trimmed = sub_polyline(pts, d0, d1, eps)
                if len(trimmed) >= 2:
                    work = trimmed
                    n_trim += int(trimmed_start) + int(trimmed_end)
                else:
                    trimmed_start = trimmed_end = False  # would delete the line; skip

            if do_extend and tolerance > 0:
                if not trimmed_start:
                    p = extend_end(i, work, True, geoms, index, tolerance, eps)
                    if p is not None:
                        work = [p] + list(work)
                        n_ext += 1
                if not trimmed_end:
                    p = extend_end(i, work, False, geoms, index, tolerance, eps)
                    if p is not None:
                        work = list(work) + [p]
                        n_ext += 1

            fi, li = flat_ref[i]
            features[fi]["parts"][li] = work
            feedback.setProgress(int(i / total * 90))

        # Reassemble one output feature per input feature.
        for feat in features:
            if feedback.isCanceled():
                break
            parts = [p for p in feat["parts"] if len(p) >= 2 and polyline_length(p) > eps]
            if not parts:
                continue
            if is_multi:
                geom = QgsGeometry.fromMultiPolylineXY(parts)
            else:
                geom = QgsGeometry.fromPolylineXY(parts[0])
            out = QgsFeature(source.fields())
            out.setAttributes(feat["attrs"])
            out.setGeometry(geom)
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)

        feedback.pushInfo(
            self.tr("Done: {ext} ends extended, {trim} ends trimmed.").format(
                ext=n_ext, trim=n_trim
            )
        )
        return {self.OUTPUT: dest_id}

    @staticmethod
    def _junction_distances(i, geom_i, geoms, index, eps):
        """Distances-along ``geom_i`` of its crossings/touches with other lines."""
        length = geom_i.length()
        out = []
        for j in index.intersects(geom_i.boundingBox()):
            if j == i:
                continue
            for x in extract_points(geom_i.intersection(geoms[j])):
                pg = QgsGeometry.fromPointXY(x)
                if geom_i.distance(pg) > eps:
                    continue
                d = geom_i.lineLocatePoint(pg)
                if 0.0 <= d <= length:
                    out.append(d)
        return out
