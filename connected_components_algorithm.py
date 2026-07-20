# -*- coding: utf-8 -*-
"""The ``Connected components`` Processing algorithm.

Labels every line with the id of the **independent sub-network** (connected
component) it belongs to. Lines are connected when their endpoints coincide, so a
clean, fully-connected network is a single component; extra components reveal gaps
or stray features — the key QA question for a road / river / utility network.

Adds two fields:

* ``cluster_id`` — component number, **ordered by size** (1 = largest network);
* ``cluster_size`` — number of edges in that component.

Output features are single-part ``LineString`` s. Run *Topology split* first if your
data has mid-segment crossings, so that lines actually share endpoints at junctions.
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
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)

try:
    from .topology_utils import data_eps, explode
except ImportError:
    from topology_utils import data_eps, explode


class ConnectedComponentsAlgorithm(QgsProcessingAlgorithm):
    """Label each line with the id of its connected sub-network."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("ConnectedComponentsAlgorithm", string)

    def createInstance(self):
        return ConnectedComponentsAlgorithm()

    def name(self):
        return "connectedcomponents"

    def displayName(self):
        return self.tr("Connected components (clusters)")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Labels every line with the id of the independent sub-network "
            "(connected component) it belongs to. Lines connect where their "
            "<b>endpoints coincide</b>.\n\n"
            "Adds <b>cluster_id</b> (ordered by size, 1 = largest network) and "
            "<b>cluster_size</b> (edge count). A fully-connected network is a single "
            "component; extra components reveal gaps or stray features.\n\n"
            "Run <i>Topology split</i> first if the data has mid-segment crossings."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input line layer"),
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Lines with cluster id"))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        # Output fields = input fields + cluster_id + cluster_size (unique names).
        out_fields = QgsFields(source.fields())
        cid_name = self._unique_name("cluster_id", out_fields)
        out_fields.append(QgsField(cid_name, QMetaType.Type.Int))
        csz_name = self._unique_name("cluster_size", out_fields)
        out_fields.append(QgsField(csz_name, QMetaType.Type.Int))

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, Qgis.WkbType.LineString, source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())
        snap = max(eps, 1e-12)

        # Explode to single-part edges, keep attributes.
        edges = []  # {"pts": [...], "attrs": [...]}
        for feat in source.getFeatures():
            for pts in explode(feat.geometry()):
                edges.append({"pts": pts, "attrs": feat.attributes()})

        if not edges:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        # Union-find over edges connected through shared endpoints.
        parent = list(range(len(edges)))

        def find(x):
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:
                parent[x], x = root, parent[x]
            return root

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        def key(pt):
            return (round(pt.x() / snap), round(pt.y() / snap))

        rep = {}  # node key -> a representative edge index
        for ei, e in enumerate(edges):
            for k in (key(e["pts"][0]), key(e["pts"][-1])):
                if k in rep:
                    union(ei, rep[k])
                else:
                    rep[k] = ei

        # Component root -> list of edge indices; then order by size (desc).
        comps = {}
        for ei in range(len(edges)):
            comps.setdefault(find(ei), []).append(ei)
        ordered = sorted(comps.values(), key=lambda m: (-len(m), min(m)))

        cluster_id = {}
        cluster_size = {}
        for cid, members in enumerate(ordered, start=1):
            for ei in members:
                cluster_id[ei] = cid
                cluster_size[ei] = len(members)

        total = len(edges)
        for ei, e in enumerate(edges):
            if feedback.isCanceled():
                break
            out = QgsFeature(out_fields)
            out.setAttributes(list(e["attrs"]) + [cluster_id[ei], cluster_size[ei]])
            out.setGeometry(QgsGeometry.fromPolylineXY(e["pts"]))
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(ei / total * 100))

        feedback.pushInfo(
            self.tr("Done: {n} components from {edges} edges (largest = cluster 1).").format(
                n=len(ordered), edges=total
            )
        )
        return {self.OUTPUT: dest_id}

    @staticmethod
    def _unique_name(base, fields):
        existing = {f.name().lower() for f in fields}
        name, k = base, 2
        while name.lower() in existing:
            name = "%s_%d" % (base, k)
            k += 1
        return name
