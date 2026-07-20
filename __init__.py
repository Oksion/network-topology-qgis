# -*- coding: utf-8 -*-
"""Network Topology — QGIS 4.0 Processing plugin.

QGIS loads a plugin by importing this package and calling ``classFactory(iface)``.
Keep imports lazy (inside the function) so that importing the package never fails
at scan time even if an optional dependency is missing.
"""


def classFactory(iface):  # noqa: N802 (name mandated by the QGIS plugin API)
    """Entry point required by QGIS.

    :param iface: A :class:`qgis.gui.QgisInterface` instance.
    :returns: The plugin object QGIS will keep alive for the session.
    """
    from .topology_split_plugin import TopologySplitPlugin

    return TopologySplitPlugin(iface)
