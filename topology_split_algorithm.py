# -*- coding: utf-8 -*-
"""The ``Topology split`` Processing algorithm.

Splits every feature of an input polygon/line layer by the geometries of a
"splitter lines" layer, preserving the original attributes on each resulting
part. Output geometry type matches the input.

QGIS 4.0 notes
--------------
* Import everything through ``qgis.core`` / ``qgis.PyQt`` (Qt6 / PyQt6 backend).
* Qt6 requires *fully scoped* enums, and QGIS 4.0 scopes its own Python enums the
  same way — hence ``QgsProcessing.SourceType.TypeVectorPolygon``,
  ``QgsFeatureSink.Flag.FastInsert``, ``Qgis.GeometryOperationResult.Success``.
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
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsSpatialIndex,
)


class TopologySplitAlgorithm(QgsProcessingAlgorithm):
    """Split input features by a layer of splitting lines."""

    INPUT = "INPUT"
    SPLIT_LAYER = "SPLIT_LAYER"
    OUTPUT = "OUTPUT"

    # --- boilerplate -------------------------------------------------------
    def tr(self, string):
        return QCoreApplication.translate("TopologySplitAlgorithm", string)

    def createInstance(self):
        return TopologySplitAlgorithm()

    def name(self):
        """Unique (within provider), lowercase, no spaces — used in the API id."""
        return "topologysplit"

    def displayName(self):
        return self.tr("Topology split")

    def group(self):
        return self.tr("Topology")

    def groupId(self):
        return "topology"

    def shortHelpString(self):
        return self.tr(
            "Splits every feature of the <b>Input layer</b> using the geometries of "
            "the <b>Split lines layer</b>.\n\n"
            "Each splitting line is applied in turn; a feature that a line fully "
            "crosses is divided into parts. Every resulting part keeps the original "
            "feature's attributes. The output geometry type matches the input.\n\n"
            "Only lines whose bounding box intersects a feature are tested, via a "
            "spatial index."
        )

    # --- parameters --------------------------------------------------------
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input layer"),
                [
                    QgsProcessing.SourceType.TypeVectorPolygon,
                    QgsProcessing.SourceType.TypeVectorLine,
                ],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SPLIT_LAYER,
                self.tr("Split lines layer"),
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Split output"),
            )
        )

    # --- execution ---------------------------------------------------------
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        split_source = self.parameterAsSource(parameters, self.SPLIT_LAYER, context)
        if split_source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.SPLIT_LAYER)
            )

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            source.fields(),
            source.wkbType(),
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Load splitter lines into memory + spatial index. Splitter layers are
        # normally small relative to the input; buffering them keeps the inner
        # loop cheap.
        split_index = QgsSpatialIndex()
        split_geoms = {}
        for i, feat in enumerate(split_source.getFeatures()):
            geom = feat.geometry()
            if geom.isEmpty():
                continue
            fid = i
            split_geoms[fid] = QgsGeometry(geom)
            indexed = QgsFeature(fid)
            indexed.setGeometry(geom)
            split_index.addFeature(indexed)

        if not split_geoms:
            feedback.pushWarning(
                self.tr("Split lines layer has no usable geometries; input copied as-is.")
            )

        total = source.featureCount()
        step = 100.0 / total if total else 0

        for current, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break

            geom = feat.geometry()
            if geom.isEmpty():
                self._write(sink, source, feat, [geom])
            else:
                candidates = split_index.intersects(geom.boundingBox())
                relevant = [split_geoms[fid] for fid in candidates if fid in split_geoms]
                parts = self._split_geometry(QgsGeometry(geom), relevant)
                self._write(sink, source, feat, parts)

            feedback.setProgress(int(current * step))

        return {self.OUTPUT: dest_id}

    # --- helpers -----------------------------------------------------------
    def _write(self, sink, source, template_feature, geometries):
        """Emit one output feature per geometry, copying the source attributes."""
        for geom in geometries:
            out = QgsFeature(source.fields())
            out.setAttributes(template_feature.attributes())
            out.setGeometry(geom)
            sink.addFeature(out, QgsFeatureSink.Flag.FastInsert)

    def _split_geometry(self, geometry, split_geoms):
        """Split ``geometry`` by every polyline part of every splitter geometry.

        Returns a list of resulting geometries (at least the original one).
        ``QgsGeometry.splitGeometry`` mutates the geometry in place to the first
        resulting part and returns the remaining parts, so we accumulate.
        """
        parts = [geometry]
        for split_geom in split_geoms:
            for line_points in self._line_parts(split_geom):
                next_parts = []
                for part in parts:
                    result, extra, _topology = part.splitGeometry(line_points, False, True)
                    next_parts.append(part)
                    if result == Qgis.GeometryOperationResult.Success and extra:
                        next_parts.extend(extra)
                parts = next_parts
        return parts

    @staticmethod
    def _line_parts(line_geom):
        """Yield each polyline (as a list of QgsPointXY) of a (multi)line geometry."""
        if line_geom.isMultipart():
            for part in line_geom.asMultiPolyline():
                if len(part) >= 2:
                    yield part
        else:
            polyline = line_geom.asPolyline()
            if len(polyline) >= 2:
                yield polyline
