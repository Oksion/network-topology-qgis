# -*- coding: utf-8 -*-
"""Plugin object: registers the Processing provider with QGIS.

This plugin has no classic menu/toolbar GUI — it exposes its functionality through
the Processing framework. ``initProcessing`` is called by QGIS both when the app
runs headless (e.g. qgis_process) and from ``initGui`` in the desktop app.
"""

import os

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator

from .topology_split_provider import TopologySplitProvider


class TopologySplitPlugin:
    """Life-cycle wrapper QGIS instantiates via ``classFactory``."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self._translator = None
        self._install_translator()

    def _install_translator(self):
        """Load the .qm for the current QGIS locale, if present.

        Must run before the provider's algorithms are displayed so that their
        ``self.tr(...)`` strings resolve. Keeps a reference so the QTranslator is
        not garbage-collected.
        """
        try:
            locale = QSettings().value("locale/userLocale", "") or ""
            lang = locale[:2] or "en"
            qm = os.path.join(
                os.path.dirname(__file__), "i18n", "network_topology_%s.qm" % lang
            )
            if os.path.exists(qm):
                translator = QTranslator()
                if translator.load(qm):
                    QCoreApplication.installTranslator(translator)
                    self._translator = translator
        except Exception:  # never let i18n break plugin load
            self._translator = None

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
