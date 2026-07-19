# -*- coding: utf-8 -*-
"""Processing provider that groups this plugin's algorithms."""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .topology_split_algorithm import TopologySplitAlgorithm


class TopologySplitProvider(QgsProcessingProvider):
    """A single-provider container. Add more algorithms in ``loadAlgorithms``."""

    def loadAlgorithms(self):
        self.addAlgorithm(TopologySplitAlgorithm())

    def id(self):
        """Stable, unique id used in algorithm ids (``topology_split:...``)."""
        return "topology_split"

    def name(self):
        """Human-readable provider name shown in the Processing Toolbox."""
        return "Topology Split"

    def longName(self):
        return "Topology Split tools"

    def icon(self):
        path = os.path.join(os.path.dirname(__file__), "resources", "icon.svg")
        if os.path.exists(path):
            return QIcon(path)
        return super().icon()
