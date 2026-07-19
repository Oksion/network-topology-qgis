# -*- coding: utf-8 -*-
"""Shared pytest fixtures.

These tests need a real PyQGIS environment. If `qgis` cannot be imported (e.g. a
plain CI runner with only `pip install pytest`), every QGIS-dependent test is
skipped rather than erroring — see the module-level guard in each test file.

Run them with QGIS's own Python, or an OSGeo4W / conda `qgis` environment, e.g.:

    # OSGeo4W shell
    python -m pytest

    # or point pytest at QGIS python explicitly
    & "C:/Program Files/QGIS 4.0/apps/Python312/python.exe" -m pytest
"""

import pytest

qgis_core = pytest.importorskip("qgis.core", reason="PyQGIS (qgis) not importable")

from qgis.core import QgsApplication  # noqa: E402


@pytest.fixture(scope="session")
def qgis_app():
    """A headless QgsApplication for the whole test session."""
    app = QgsApplication([], False)
    app.initQgis()
    yield app
    app.exitQgis()
