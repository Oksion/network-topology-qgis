# -*- coding: utf-8 -*-
"""The ``Collapse pseudo-nodes`` Processing algorithm.

The inverse of noding: merges chains of lines that connect only through
**degree-2 nodes** (a "pseudo-node" — a shared endpoint where exactly two line ends
meet) into single lines that run from one real junction/dead-end to the next.

* Lines are joined only where their **endpoints coincide** (run *Topology split*
  first if your data has mid-segment crossings).
* An optional **Group field** makes a pseudo-node a barrier unless both lines share
  the same value — so merging never crosses an attribute boundary.
* Output features are single-part ``LineString`` s. The merged line inherits the
  attributes of its **longest** input segment (documented, since other attributes
  along a chain may differ).

Geometry is treated as planar 2D; original vertices are preserved.
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureSink,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)

try:
    from .topology_utils import data_eps, dist, explode, polyline_length
except ImportError:
    from topology_utils import data_eps, dist, explode, polyline_length


class PseudoNodeCollapseAlgorithm(QgsProcessingAlgorithm):
    """Merge degree-2 chains into single lines."""

    INPUT = "INPUT"
    GROUP_FIELD = "GROUP_FIELD"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        return QCoreApplication.translate("PseudoNodeCollapseAlgorithm", string)

    def createInstance(self):
        return PseudoNodeCollapseAlgorithm()

    def name(self):
        return "collapsepseudonodes"

    def displayName(self):
        return self.tr("Collapse pseudo-nodes")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Merges chains of lines that meet only at <b>degree-2 nodes</b> "
            "(pseudo-nodes) into single lines running junction-to-junction.\n\n"
            "• Lines are joined only where their <b>endpoints coincide</b>. If your "
            "data has mid-segment crossings, run <i>Topology split</i> first.\n"
            "• Nodes where 3+ lines meet, and dead-ends, are kept.\n"
            "• <b>Group field</b> (optional): only merge across a node when both "
            "lines share the same value of this field.\n\n"
            "Output is single-part LineStrings; a merged line inherits the attributes "
            "of its longest input segment."
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
            QgsProcessingParameterField(
                self.GROUP_FIELD,
                self.tr("Group field (only merge where equal)"),
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Merged lines"))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        group_field = self.parameterAsString(parameters, self.GROUP_FIELD, context)
        gfi = source.fields().indexOf(group_field) if group_field else -1

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), Qgis.WkbType.LineString, source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        eps = data_eps(source.sourceExtent())
        snap = max(eps, 1e-12)

        # Explode to single-part edges; keep attributes + a group value per edge.
        edges = []   # {"pts": [...], "attrs": [...], "grp": value_or_None, "len": float}
        for feat in source.getFeatures():
            attrs = feat.attributes()
            grp = attrs[gfi] if gfi >= 0 else None
            for pts in explode(feat.geometry()):
                edges.append({"pts": pts, "attrs": attrs, "grp": grp,
                              "len": polyline_length(pts)})

        if not edges:
            feedback.pushWarning(self.tr("No usable line geometries in the input."))
            return {self.OUTPUT: dest_id}

        def key(pt):
            return (round(pt.x() / snap), round(pt.y() / snap))

        # node -> list of (edge_index, end) where end 0=start, 1=end
        node_map = {}
        starts, ends = [], []
        for ei, e in enumerate(edges):
            ks, ke = key(e["pts"][0]), key(e["pts"][-1])
            starts.append(ks)
            ends.append(ke)
            node_map.setdefault(ks, []).append((ei, 0))
            node_map.setdefault(ke, []).append((ei, 1))

        def degree(k):
            return len(node_map.get(k, ()))

        used = [False] * len(edges)

        def walk(start_key, edge0, end0):
            """Build a chain of (edge_index, forward) starting at start_key."""
            chain = []
            cur_ei, cur_end, cur_key = edge0, end0, start_key
            grp_val = edges[cur_ei]["grp"]
            while True:
                used[cur_ei] = True
                forward = (cur_end == 0)  # start is at cur_key → traverse start→end
                chain.append((cur_ei, forward))
                next_key = ends[cur_ei] if forward else starts[cur_ei]
                if degree(next_key) != 2:
                    break
                arriving = (cur_ei, 1 if forward else 0)
                others = [e for e in node_map[next_key] if e != arriving]
                if not others:
                    break
                n_ei, n_end = others[0]
                if used[n_ei]:
                    break  # closed loop
                if gfi >= 0 and edges[n_ei]["grp"] != grp_val:
                    break  # attribute barrier
                cur_ei, cur_end, cur_key = n_ei, n_end, next_key
            return chain

        chains = []
        # Seed chains from every non-degree-2 node (junctions and dead-ends).
        for k, incident in node_map.items():
            if degree(k) == 2:
                continue
            for ei, end in incident:
                if not used[ei]:
                    chains.append(walk(k, ei, end))
        # Remaining edges form pure loops (all nodes degree 2).
        for ei in range(len(edges)):
            if not used[ei]:
                chains.append(walk(starts[ei], ei, 0))

        # Emit one merged single-part line per chain.
        n_out = 0
        for chain in chains:
            if feedback.isCanceled():
                break
            coords = []
            for ei, forward in chain:
                seq = edges[ei]["pts"] if forward else list(reversed(edges[ei]["pts"]))
                if not coords:
                    coords.extend(seq)
                else:
                    coords.extend(seq[1:] if dist(seq[0], coords[-1]) <= snap else seq)
            if len(coords) < 2 or polyline_length(coords) <= eps:
                continue
            # attributes from the longest edge in the chain
            rep = max((edges[ei] for ei, _ in chain), key=lambda e: e["len"])
            out = QgsFeature(source.fields())
            out.setAttributes(rep["attrs"])
            out.setGeometry(QgsGeometry.fromPolylineXY(coords))
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)
            n_out += 1

        feedback.pushInfo(
            self.tr("Done: {out} merged lines from {edges} input segments.").format(
                out=n_out, edges=len(edges)
            )
        )
        return {self.OUTPUT: dest_id}
