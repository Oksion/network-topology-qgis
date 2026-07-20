"""The ``Topology split`` Processing algorithm.

Takes a **single line layer** and rebuilds its topology *against itself*:

1. Works on a line (polyline) layer.
2. Splits where the **end of a line touches another line** (T-junctions).
3. Preserves the original geometry of the lines (no vertices are moved or dropped).
4. If a line's dangling end comes **within a configurable tolerance** of another
   line, the end is **extended along its own direction** until it meets that line.
5. Splits **both** lines at every crossing (X-intersections) too.
6. Output features are **single-part** ``LineString`` s (never ``MultiLineString``).
7. Attributes are inherited by every resulting part.

Geometry is treated as planar 2D (Z/M dropped). Shared helpers live in
``topology_utils``.
"""

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureSink,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)
from qgis.PyQt.QtCore import QCoreApplication

try:  # loaded as part of the plugin package
    from .topology_utils import (
        build_line_index,
        data_eps,
        explode,
        extend_end,
        extract_points,
        split_polyline,
    )
except ImportError:  # loaded as a plain module (tests / console)
    from topology_utils import (
        build_line_index,
        data_eps,
        explode,
        extend_end,
        extract_points,
        split_polyline,
    )


class TopologySplitAlgorithm(QgsProcessingAlgorithm):
    """Self-node a line layer: extend dangles, split at all nodes, inherit attrs."""

    INPUT = "INPUT"
    TOLERANCE = "TOLERANCE"
    OUTPUT = "OUTPUT"

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
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Noded lines"))
        )

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
            Qgis.WkbType.LineString,
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())

        # step 0: explode to single-part polylines, keep attributes
        lines = []
        for feat in source.getFeatures():
            if feedback.isCanceled():
                return {self.OUTPUT: dest_id}
            for pts in explode(feat.geometry()):
                lines.append({"pts": pts, "attrs": feat.attributes()})

        if not lines:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        geoms = [QgsGeometry.fromPolylineXY(line["pts"]) for line in lines]
        index = build_line_index(geoms)

        # step 4: extend dangling ends
        extended = 0
        if tolerance > 0:
            feedback.pushInfo(self.tr("Extending dangling ends…"))
            for i, line in enumerate(lines):
                if feedback.isCanceled():
                    return {self.OUTPUT: dest_id}
                for at_start in (True, False):
                    new_pt = extend_end(
                        i, line["pts"], at_start, geoms, index, tolerance, eps
                    )
                    if new_pt is not None:
                        if at_start:
                            line["pts"].insert(0, new_pt)
                        else:
                            line["pts"].append(new_pt)
                        extended += 1
                feedback.setProgress(int(i / len(lines) * 40))
            geoms = [QgsGeometry.fromPolylineXY(line["pts"]) for line in lines]
            index = build_line_index(geoms)

        # steps 2 & 5: collect node points per line
        feedback.pushInfo(self.tr("Computing intersections…"))
        cut_points = [[] for _ in lines]
        for i, geom_i in enumerate(geoms):
            if feedback.isCanceled():
                return {self.OUTPUT: dest_id}
            for j in index.intersects(geom_i.boundingBox()):
                if j <= i:
                    continue
                pts = extract_points(geom_i.intersection(geoms[j]))
                if pts:
                    cut_points[i].extend(pts)
                    cut_points[j].extend(pts)
            feedback.setProgress(40 + int(i / len(lines) * 40))

        # steps 6, 3 & 7: cut each line at its nodes, write parts
        feedback.pushInfo(self.tr("Splitting lines at nodes…"))
        n_out = 0
        for i, line in enumerate(lines):
            if feedback.isCanceled():
                break
            geom_i = geoms[i]
            length = geom_i.length()
            cut_dists = []
            for p in cut_points[i]:
                pgeom = QgsGeometry.fromPointXY(p)
                if geom_i.distance(pgeom) > eps:
                    continue
                d = geom_i.lineLocatePoint(pgeom)
                if 0.0 <= d <= length:
                    cut_dists.append(d)
            for part_pts in split_polyline(line["pts"], cut_dists, eps):
                out = QgsFeature(source.fields())
                out.setAttributes(line["attrs"])
                out.setGeometry(QgsGeometry.fromPolylineXY(part_pts))
                sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
                n_out += 1
            feedback.setProgress(80 + int(i / len(lines) * 20))

        feedback.pushInfo(
            self.tr(
                "Done: {parts} parts from {inputs} lines, {ext} ends extended."
            ).format(parts=n_out, inputs=len(lines), ext=extended)
        )
        return {self.OUTPUT: dest_id}
