# -*- coding: utf-8 -*-
"""Plugin object: registers the Processing provider with QGIS.

This plugin has no classic menu/toolbar GUI — it exposes its functionality through
the Processing framework. ``initProcessing`` is called by QGIS both when the app
runs headless (e.g. qgis_process) and from ``initGui`` in the desktop app.
"""

from qgis.core import QgsApplication

from .topology_split_provider import TopologySplitProvider


class TopologySplitPlugin:
    """Life-cycle wrapper QGIS instantiates via ``classFactory``."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        """Create and register the Processing provider (headless-safe)."""
        if self.provider is None:
            self.provider = TopologySplitProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Called by the desktop app; only needs to wire up Processing here."""
        self.initProcessing()

    def unload(self):
        """Remove the provider so the plugin can be reloaded cleanly."""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
