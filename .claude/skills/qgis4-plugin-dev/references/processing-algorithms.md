# Anatomy of a QGIS Processing algorithm

A Processing plugin = a `QgsProcessingProvider` that registers one or more
`QgsProcessingAlgorithm` subclasses. No toolbar/menu code required.

## Provider

```python
class MyProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(MyAlgorithm())
    def id(self):        return "my_provider"     # stable id -> "my_provider:algname"
    def name(self):      return "My Provider"     # shown in the Toolbox
    def icon(self):      return QIcon(...)         # from a file path, not a .qrc
```

Register it in the plugin's `initProcessing()`:
```python
QgsApplication.processingRegistry().addProvider(self.provider)
```
and remove it in `unload()` with `removeProvider(...)` so reloads are clean.

## Algorithm skeleton

```python
class MyAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def createInstance(self):  return MyAlgorithm()   # MUST return a fresh instance
    def name(self):            return "myalg"          # lowercase, no spaces
    def displayName(self):     return self.tr("My Alg")
    def group(self):           return self.tr("Group")
    def groupId(self):         return "group"
    def shortHelpString(self): return self.tr("What it does.")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, self.tr("Input"),
            [QgsProcessing.SourceType.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, self.tr("Output")))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            source.fields(), source.wkbType(), source.sourceCrs())
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        total = source.featureCount()
        step = 100.0 / total if total else 0
        for i, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            # ... transform feat ...
            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(i * step))
        return {self.OUTPUT: dest_id}
```

## Key conventions

- **`createInstance` returns a new object** — the registry clones the algorithm per run.
- **Honour `feedback`**: check `isCanceled()`, call `setProgress()`, use
  `pushInfo/pushWarning` for messages.
- **Report bad params** with `invalidSourceError` / `invalidSinkError` wrapped in
  `QgsProcessingException`.
- **Wrap user-facing strings in `self.tr(...)`** for translation.
- Algorithm id seen by users/`qgis_process` is `"<provider id>:<name()>"`.

## Running / testing

```bash
qgis_process run "my_provider:myalg" --INPUT=in.gpkg --OUTPUT=out.gpkg
```
In tests, drive it directly:
```python
alg = MyAlgorithm(); alg.initAlgorithm()
results = alg.run({"INPUT": layer, "OUTPUT": "memory:"},
                  QgsProcessingContext(), QgsProcessingFeedback())[0]
```

## Useful building blocks

- `QgsSpatialIndex` — index one layer to avoid O(n·m) geometry tests.
- `QgsGeometry` ops: `intersection`, `difference`, `splitGeometry`, `combine`,
  `buffer`, `makeValid`. Note `splitGeometry` **mutates in place** and returns the
  extra parts + a result code (`Qgis.GeometryOperationResult`).
- Parameter types: `...ParameterFeatureSource/Sink`, `...ParameterField`,
  `...ParameterNumber`, `...ParameterBoolean`, `...ParameterEnum`, `...ParameterCrs`.
