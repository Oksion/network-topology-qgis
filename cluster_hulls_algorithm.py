# -*- coding: utf-8 -*-
"""The ``Cluster extents`` Processing algorithm.

Produces **one polygon per connected sub-network** (cluster) of a line layer — a
convex hull, an axis-aligned bounding box, or an oriented bounding box. Handy for
seeing where the disconnected clusters are (e.g. a stray "island" far from the main
network) and deciding which to bridge or drop.

Each polygon carries: ``cluster_id`` (ordered by size, 1 = largest network),
``edge_count`` (edges in the cluster) and ``length`` (total length of its edges).

Lines belong to the same cluster when their endpoints coincide — run *Topology
split* first if the data has mid-segment crossings. A fully-collinear cluster (a
single straight run) yields a zero-area hull; that's expected.
"""

from qgis.PyQt.QtCore import QCoreApplication, QMetaType
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)

try:
    from .topology_utils import build_components, data_eps, explode, polyline_length
except ImportError:
    from topology_utils import build_components, data_eps, explode, polyline_length


class ClusterHullsAlgorithm(QgsProcessingAlgorithm):
    """One hull / bbox polygon per connected sub-network."""

    INPUT = "INPUT"
    METHOD = "METHOD"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("ClusterHullsAlgorithm", string)

    def createInstance(self):
        return ClusterHullsAlgorithm()

    def name(self):
        return "clusterhulls"

    def displayName(self):
        return self.tr("Cluster extents (hull / bbox)")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Outputs one polygon per connected sub-network (cluster) of the line "
            "layer — a convex hull, bounding box, or oriented bounding box.\n\n"
            "Each polygon carries <b>cluster_id</b> (ordered by size, 1 = largest), "
            "<b>edge_count</b> and <b>length</b>. Use it to spot disconnected clusters "
            "and decide which to bridge or drop.\n\n"
            "Lines join where their <b>endpoints coincide</b>; run <i>Topology split</i> "
            "first if the data has mid-segment crossings."
        )

    def _methods(self):
        return [
            self.tr("Convex hull"),
            self.tr("Bounding box"),
            self.tr("Oriented bounding box"),
        ]

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input line layer"),
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.METHOD,
                self.tr("Cluster shape"),
                options=self._methods(),
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Cluster polygons"),
                type=QgsProcessing.SourceType.TypeVectorPolygon,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        method = self.parameterAsEnum(parameters, self.METHOD, context)

        out_fields = QgsFields()
        out_fields.append(QgsField("cluster_id", QMetaType.Type.Int))
        out_fields.append(QgsField("edge_count", QMetaType.Type.Int))
        out_fields.append(QgsField("length", QMetaType.Type.Double))

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, Qgis.WkbType.Polygon, source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())
        snap = max(eps, 1e-12)

        edge_pts = []
        for feat in source.getFeatures():
            for pts in explode(feat.geometry()):
                edge_pts.append(pts)

        if not edge_pts:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        components = build_components(edge_pts, snap)

        n_out = 0
        total = len(components)
        for cid, members in enumerate(components, start=1):
            if feedback.isCanceled():
                break
            pts = []
            length = 0.0
            for ei in members:
                pts.extend(edge_pts[ei])
                length += polyline_length(edge_pts[ei])

            hull = self._hull(pts, method)
            if hull is None or hull.isEmpty():
                continue

            out = QgsFeature(out_fields)
            out.setAttributes([cid, len(members), length])
            out.setGeometry(hull)
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
            n_out += 1
            feedback.setProgress(int(cid / total * 100))

        feedback.pushInfo(self.tr("Done: {n} cluster polygons.").format(n=n_out))
        return {self.OUTPUT: dest_id}

    @staticmethod
    def _hull(points, method):
        """Build a hull/bbox polygon for a cluster's points (method: 0/1/2).

        Always returns a Polygon: for a fully-collinear cluster the convex hull /
        oriented box degenerates to a line, so we fall back to the axis-aligned box.
        """
        g = QgsGeometry.fromMultiPointXY(points)
        if method == 1:  # axis-aligned bounding box
            return QgsGeometry.fromRect(g.boundingBox())
        if method == 2:  # oriented bounding box
            res = g.orientedMinimumBoundingBox()
            hull = res[0] if isinstance(res, tuple) else res
        else:  # 0: convex hull
            hull = g.convexHull()
        if hull is None or hull.isEmpty() or int(hull.type()) != 2:
            hull = QgsGeometry.fromRect(g.boundingBox())
        return hull
