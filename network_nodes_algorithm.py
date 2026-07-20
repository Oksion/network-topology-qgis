"""The ``Network nodes`` Processing algorithm.

Emits one **point per node** of a line network, with its **degree** (how many line
ends meet there) and a **type** derived from the degree:

* ``dangle``   — degree 1 (dead-end / free end; a river source, a road stub);
* ``pseudo``   — degree 2 (two lines meet end-to-end; a collapse candidate);
* ``junction`` — degree 3+ (a real crossroad / confluence / branch).

A diagnostic (QA) companion to the cleaning tools: dangles feed *Resolve dangles*,
pseudo-nodes feed *Collapse pseudo-nodes*.

Nodes are the **endpoints of edges** that coincide — run *Topology split* first if
the data has mid-segment crossings, otherwise those crossings are not counted as
nodes. ``node_type`` values are fixed English codes so filtering is locale-stable.
"""

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
from qgis.PyQt.QtCore import QCoreApplication, QMetaType

try:
    from .topology_utils import data_eps, explode
except ImportError:
    from topology_utils import data_eps, explode


class NetworkNodesAlgorithm(QgsProcessingAlgorithm):
    """One point per node, labelled with degree and type."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("NetworkNodesAlgorithm", string)

    def createInstance(self):
        return NetworkNodesAlgorithm()

    def name(self):
        return "networknodes"

    def displayName(self):
        return self.tr("Network nodes (degree / type)")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Emits one point per node of the line network, with its <b>degree</b> "
            "(how many line ends meet there) and a <b>type</b>:\n\n"
            "• <b>dangle</b> — degree 1 (dead-end / free end);\n"
            "• <b>pseudo</b> — degree 2 (two lines end-to-end);\n"
            "• <b>junction</b> — degree 3+ (a real crossroad / confluence / branch).\n\n"
            "Nodes are the coinciding <b>endpoints of edges</b> — run "
            "<i>Topology split</i> first if the data has mid-segment crossings. "
            "The <b>node_type</b> values are fixed English codes "
            "(dangle/pseudo/junction) for locale-stable filtering."
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
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Network nodes"),
                type=QgsProcessing.SourceType.TypeVectorPoint,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        out_fields = QgsFields()
        out_fields.append(QgsField("node_id", QMetaType.Type.Int))
        out_fields.append(QgsField("degree", QMetaType.Type.Int))
        out_fields.append(QgsField("node_type", QMetaType.Type.QString))
        out_fields.append(QgsField("edge_count", QMetaType.Type.Int))

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            out_fields,
            Qgis.WkbType.Point,
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())
        snap = max(eps, 1e-12)

        def key(pt):
            return (round(pt.x() / snap), round(pt.y() / snap))

        # node key -> [incident-end count, representative QgsPointXY]
        nodes = {}
        for feat in source.getFeatures():
            if feedback.isCanceled():
                return {self.OUTPUT: dest_id}
            for pts in explode(feat.geometry()):
                for endpt in (pts[0], pts[-1]):
                    k = key(endpt)
                    if k in nodes:
                        nodes[k][0] += 1
                    else:
                        nodes[k] = [1, endpt]

        if not nodes:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        counts = {"dangle": 0, "pseudo": 0, "junction": 0}
        total = len(nodes)
        for node_id, (degree, pt) in enumerate(nodes.values(), start=1):
            if feedback.isCanceled():
                break
            node_type = (
                "dangle" if degree == 1 else "pseudo" if degree == 2 else "junction"
            )
            counts[node_type] += 1
            out = QgsFeature(out_fields)
            out.setAttributes([node_id, degree, node_type, degree])
            out.setGeometry(QgsGeometry.fromPointXY(pt))
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(node_id / total * 100))

        feedback.pushInfo(
            self.tr("Done: {n} nodes — {d} dangles, {p} pseudo, {j} junctions.").format(
                n=total, d=counts["dangle"], p=counts["pseudo"], j=counts["junction"]
            )
        )
        return {self.OUTPUT: dest_id}
