# -*- coding: utf-8 -*-
"""Processing provider that groups this plugin's algorithms."""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .connected_components_algorithm import ConnectedComponentsAlgorithm
from .dangle_resolver_algorithm import DangleResolverAlgorithm
from .pseudonode_collapse_algorithm import PseudoNodeCollapseAlgorithm
from .topology_split_algorithm import TopologySplitAlgorithm


class TopologySplitProvider(QgsProcessingProvider):
    """Container for the Network Topology toolkit. Register algorithms here."""

    def loadAlgorithms(self):
        self.addAlgorithm(TopologySplitAlgorithm())
        self.addAlgorithm(DangleResolverAlgorithm())
        self.addAlgorithm(PseudoNodeCollapseAlgorithm())
        self.addAlgorithm(ConnectedComponentsAlgorithm())

    def id(self):
        """Stable, unique id used in algorithm ids (``network_topology:...``)."""
        return "network_topology"

    def name(self):
        """Human-readable provider name shown in the Processing Toolbox."""
        return "Network Topology"

    def longName(self):
        return "Network Topology tools"

    def icon(self):
        path = os.path.join(os.path.dirname(__file__), "resources", "icon.svg")
        if os.path.exists(path):
            return QIcon(path)
        return super().icon()
