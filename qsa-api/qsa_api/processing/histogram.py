# coding: utf8
from multiprocessing import Manager, Process
from qgis.core import QgsProject, QgsRasterDataProvider, QgsRasterBandStats

from ..utils import logger


class Histogram:
    def __init__(self, project_uri: str, layer: str) -> None:
        self.layer = layer
        self.project_uri = project_uri

    def process(self, mini, maxi, count) -> bool | dict:
        # Some kind of cache is bothering us because when a raster layer is
        # added on S3, we cannot open it with GDAL provider later. The
        # QgsApplication needs to be restarted... why???
        manager = Manager()
        out = manager.dict()

        p = Process(
            target=Histogram._process,
            args=(self.project_uri, self.layer, mini, maxi, count, out),
        )
        p.start()
        p.join()

        if "histo" in out:
            return out["histo"].copy()

        return {}

    @staticmethod
    def _process(
        project_uri: str, layerName: str, mini, maxi, count, out: dict
    ) -> None:
        log = logger()

        project = QgsProject.instance()
        project.read(project_uri)
        layer = project.mapLayersByName(layerName)[0]

        rect = layer.extent()
        log.debug("[Histogram] extent: %s", rect.area())
        log.debug("[Histogram] width: %s", rect.width())
        log.debug("[Histogram] height: %s", rect.height())

        data_provider: QgsRasterDataProvider = layer.dataProvider()
        x_size = data_provider.xSize()
        y_size = data_provider.ySize()
        log.debug("[Histogram] size: %s x %s", x_size, y_size)

        if not data_provider.isValid():
            out["histo"] = {}
            return

        histo = {}
        for band in range(layer.bandCount()):
            band_id = band + 1
            stats = data_provider.bandStatistics(
                band_id,
                QgsRasterBandStats.Min | QgsRasterBandStats.Max,
                layer.extent(),
                250000,  # sample size, 250000 is for a 500x500 image => give the size of the histogram
            )
            hist = data_provider.histogram(
                band + 1,
                0,
                stats.minimumValue,
                stats.maximumValue,
                layer.extent(),
                0, # 250000
            )

            log.debug("[Histogram] size: %s", len(hist.histogramVector))
            log.debug("[Histogram2] size: %s", len(hist2.histogramVector))

            histo[band + 1] = {}
            histo[band + 1]["min"] = hist.minimum
            histo[band + 1]["max"] = hist.maximum
            histo[band + 1]["values"] = hist.histogramVector

        out["histo"] = histo
