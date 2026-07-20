# -*- coding: utf-8 -*-
"""Regenerate the translation source (.ts) from the algorithm modules.

pylupdate6 needs QGIS's Qt6 environment, so run this through the QGIS python:

    "C:/Program Files/QGIS 4.2.0/bin/python-qgis.bat" tools/update_ts.py

Then fill in the new <translation> entries and compile with lrelease (see
docs/development.md). Existing translations in the .ts are preserved by pylupdate6.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SOURCES = [
    "topology_split_algorithm.py",
    "dangle_resolver_algorithm.py",
    "pseudonode_collapse_algorithm.py",
    "connected_components_algorithm.py",
]
TS = "i18n/network_topology_ru.ts"

sys.argv = ["pylupdate6", *SOURCES, "-ts", TS]
from PyQt6.lupdate.pylupdate import main  # noqa: E402

main()
print("Updated %s" % TS)
