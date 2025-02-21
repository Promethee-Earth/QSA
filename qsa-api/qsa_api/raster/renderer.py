# coding: utf8

from enum import Enum
from pathlib import Path
from wrappers import Result, Err
from properties_builder import PropertiesBuilder

from qgis.core import (
    QgsRasterLayer,
    QgsRasterBandStats,
    QgsRasterMinMaxOrigin,
    QgsContrastEnhancement,
    QgsSingleBandGrayRenderer,
    QgsMultiBandColorRenderer,
    QgsSingleBandPseudoColorRenderer,
)

ContrastEnhancementAlgorithm = (
    QgsContrastEnhancement.ContrastEnhancementAlgorithm
)


class RasterSymbologyRendererErr(Enum):
    NotImplementedError = "NotImplementedError"


class RasterSymbologyRenderer:
    class Color(Enum):
        GRAY = 0
        RED = 1
        GREEN = 2
        BLUE = 3

    class Type(Enum):
        SINGLE_BAND_GRAY = QgsSingleBandGrayRenderer(None, 1).type()
        SINGLE_BAND_PSEUDOCOLOR = QgsSingleBandPseudoColorRenderer(
            None, 1
        ).type()
        MULTI_BAND_COLOR = QgsMultiBandColorRenderer(None, 1, 1, 1).type()

    def __init__(self, name: str) -> None:
        self.renderer = None
        self.contrast_algorithm = None
        self.contrast_limits = QgsRasterMinMaxOrigin.Limits.MinMax

        self.gray_min = None
        self.gray_max = None
        self.red_min = None
        self.red_max = None
        self.green_min = None
        self.green_max = None
        self.blue_min = None
        self.blue_max = None

        if name == RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY.value:
            self.renderer = QgsSingleBandGrayRenderer(None, 1)
        elif name == RasterSymbologyRenderer.Type.MULTI_BAND_COLOR.value:
            self.renderer = QgsMultiBandColorRenderer(None, 1, 1, 1)
        elif (
            name == RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR.value
        ):
            self.renderer = QgsSingleBandPseudoColorRenderer(None, 1)

    @property
    def type(self):
        match self.renderer.type():
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY.value:
                return RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR.value:
                return RasterSymbologyRenderer.Type.MULTI_BAND_COLOR
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR.value:
                return RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR
            case _:
                return None

    def load(self, properties: dict) -> (bool | str):
        if not self.renderer:
            return False, "Invalid renderer"
        if "contrast_enhancement" in properties:
            self._load_contrast_enhancement(properties["contrast_enhancement"])
        match self.type:
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                PropertiesBuilder.load_multibandcolor_properties(
                    self, properties)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                PropertiesBuilder._load_singlebandgray_properties(
                    self, properties)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
                PropertiesBuilder._load_singlebandpseudocolor_properties(
                    self, properties)
            case _:
                return False, "Invalid renderer type"
        return True, ""

    def refresh_min_max(self, layer: QgsRasterLayer) -> None:
        # see QgsRasterMinMaxWidget::doComputations
        # early break
        if (layer.renderer().minMaxOrigin().limits() == QgsRasterMinMaxOrigin.Limits.None_):
            return
        # refresh according to renderer
        match self.type:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                self._refresh_min_max_singlebandgray(layer)
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                self._refresh_min_max_multibandcolor(layer)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
                self._refresh_min_max_singlebandpseudocolor(layer)

    def process_renderering(self, raster: QgsRasterLayer, rendering: dict) -> None:
        # config rendering
        mapping = {
            "gamma": lambda v: raster.brightnessFilter().setGamma(float(v)),
            "brightness": lambda v: raster.brightnessFilter().setBrightness(int(v)),
            "contrast": lambda v: raster.brightnessFilter().setContrast(int(v)),
            "saturation": lambda v: raster.hueSaturationFilter().setSaturation(int(v)),
        }
        for key, action in mapping.items():
            if key in rendering:
                action(rendering[key])

    def manage_min_max_limits(self, raster: QgsRasterLayer) -> Result[None, RasterSymbologyRendererErr]:
        match  self.contrast_limits:
            # user defined min/max
            case QgsRasterMinMaxOrigin.Limits.None_:
                self.__set_user_defined_min_max(raster)
            # default min/max
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                pass
            # cumulative cut min/max
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__set_cumulative_cut_min_max(
                    raster, QgsRasterMinMaxOrigin.CUMULATIVE_CUT_UPPER, QgsRasterMinMaxOrigin.CUMULATIVE_CUT_LOWER)

    def __set_user_defined_min_max(self, raster: QgsRasterLayer):
        match self.type:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                ce = QgsContrastEnhancement(
                    raster.renderer().contrastEnhancement())
                self.__set_min_max(ce, raster, self.Color.GRAY)
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                red_ce = QgsContrastEnhancement(
                    raster.renderer().redContrastEnhancement())
                self.__set_min_max(red_ce, raster, self.Color.RED)
                green_ce = QgsContrastEnhancement(
                    raster.renderer().greenContrastEnhancement())
                self.__set_min_max(green_ce, raster, self.Color.GREEN)
                blue_ce = QgsContrastEnhancement(
                    raster.renderer().blueContrastEnhancement())
                self.__set_min_max(blue_ce, raster, self.Color.BLUE)

    def __set_cumulative_cut_min_max(self, raster: QgsRasterLayer, max_cut: float, min_cut: float):
        min_max = QgsRasterMinMaxOrigin()
        min_max.setLimits(QgsRasterMinMaxOrigin.Limits.CumulativeCut)
        min_max.setCumulativeCutUpper(
            QgsRasterMinMaxOrigin.CUMULATIVE_CUT_UPPER)
        min_max.setCumulativeCutLower(
            QgsRasterMinMaxOrigin.CUMULATIVE_CUT_LOWER)
        raster.renderer().setMinMaxOrigin(min_max)

    def __set_min_max(self, contrast_enhancement: QgsContrastEnhancement, raster: QgsRasterLayer, color: Color):
        match color:
            case self.Color.RED:
                if self.red_min is not None:
                    contrast_enhancement.setMinimumValue(self.red_min)
                if self.red_max is not None:
                    contrast_enhancement.setMaximumValue(self.red_max)
                raster.renderer().setRedContrastEnhancement(contrast_enhancement)
            case self.Color.GREEN:
                contrast_enhancement.setMinimumValue(self.green_min)
                contrast_enhancement.setMaximumValue(self.green_max)
                raster.renderer().setGreenContrastEnhancement(contrast_enhancement)
            case self.Color.BLUE:
                contrast_enhancement.setMinimumValue(self.blue_min)
                contrast_enhancement.setMaximumValue(self.blue_max)
                raster.renderer().setBlueContrastEnhancement(contrast_enhancement)
            case self.Color.GRAY:
                if self.gray_min is not None:
                    contrast_enhancement.setMinimumValue(self.gray_min)
                if self.gray_max is not None:
                    contrast_enhancement.setMaximumValue(self.gray_max)
                raster.renderer().setContrastEnhancement(contrast_enhancement)

    def _refresh_min_max_multibandcolor(self, layer: QgsRasterLayer) -> None:
        renderer = QgsMultiBandColorRenderer(layer.renderer())
        
        # early break
        alg = renderer.redContrastEnhancement.contrastEnhancementAlgorithm()
        min_max_origin = renderer.minMaxOrigin().limits()
        if (alg == ContrastEnhancementAlgorithm.NoEnhancement):
            return

        # compute min/max with "Accuracy: estimate"
        match min_max_origin:
            case QgsRasterMinMaxOrigin.Limits.None_:
                return
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                self.__compute_multi_band_min_max(layer, renderer)
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__compute_multi_band_min_max(layer, renderer)
                min_max_cut = QgsRasterMinMaxOrigin()
                min_max_cut.setLimits(QgsRasterMinMaxOrigin.Limits.CumulativeCut)
                min_max_cut.setCumulativeCutUpper(QgsRasterMinMaxOrigin.CUMULATIVE_CUT_UPPER)
                min_max_cut.setCumulativeCutLower(QgsRasterMinMaxOrigin.CUMULATIVE_CUT_LOWER)
                layer.renderer().setMinMaxOrigin(min_max_origin)
    
    def __compute_multi_band_min_max(self, layer: QgsRasterLayer, renderer: QgsMultiBandColorRenderer) -> None:
        red_ce = QgsContrastEnhancement(renderer.redContrastEnhancement())
        green_ce = QgsContrastEnhancement(renderer.greenContrastEnhancement())
        blue_ce = QgsContrastEnhancement(renderer.blueContrastEnhancement())
        red_band = renderer.redBand()
        red_stats = layer.dataProvider().bandStatistics(
            red_band,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        red_ce.setMinimumValue(red_stats.minimumValue)
        red_ce.setMaximumValue(red_stats.maximumValue)

        green_band = renderer.greenBand()
        green_stats = layer.dataProvider().bandStatistics(
            green_band,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        green_ce.setMinimumValue(green_stats.minimumValue)
        green_ce.setMaximumValue(green_stats.maximumValue)

        blue_band = renderer.blueBand()
        blue_stats = layer.dataProvider().bandStatistics(
            blue_band,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        blue_ce.setMinimumValue(blue_stats.minimumValue)
        blue_ce.setMaximumValue(blue_stats.maximumValue)
        layer.renderer().setRedContrastEnhancement(red_ce)
        layer.renderer().setGreenContrastEnhancement(green_ce)
        layer.renderer().setBlueContrastEnhancement(blue_ce)
        

    def _refresh_min_max_singlebandgray(self, layer: QgsRasterLayer) -> None:
        ce = QgsContrastEnhancement(layer.renderer().contrastEnhancement())

        # early break
        alg = ce.contrastEnhancementAlgorithm()
        if (
            alg == ContrastEnhancementAlgorithm.NoEnhancement
            or alg == ContrastEnhancementAlgorithm.UserDefinedEnhancement
        ):
            return

        match alg:
            case ContrastEnhancementAlgorithm.NoEnhancement:
                return
            case ContrastEnhancementAlgorithm.StretchToMinimumMaximum:
                min_max_origin = layer.renderer().minMaxOrigin().limits()
                if min_max_origin == QgsRasterMinMaxOrigin.Limits.MinMax:
                    # Accuracy : estimate
                    stats = layer.dataProvider().bandStatistics(
                        1,
                        QgsRasterBandStats.Min | QgsRasterBandStats.Max,
                        layer.extent(),
                        250000,
                    )

                    ce.setMinimumValue(stats.minimumValue)
                    ce.setMaximumValue(stats.maximumValue)

                layer.renderer().setContrastEnhancement(ce)
            case ContrastEnhancementAlgorithm.UserDefinedEnhancement:
                return
            case _:
                return
        # compute min/max

    def _refresh_min_max_singlebandpseudocolor(self, layer: QgsRasterLayer) -> None:
        # compute min/max
        min_max_origin = layer.renderer().minMaxOrigin().limits()
        match min_max_origin:
            case QgsRasterMinMaxOrigin.Limits.None_:
                return
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                return
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                # Accuracy : estimate
                stats = layer.dataProvider().bandStatistics(
                    1,
                    QgsRasterBandStats.Min | QgsRasterBandStats.Max,
                    layer.extent(),
                    250000,
                )
                layer.renderer().setClassificationMin(stats.minimumValue)
                layer.renderer().setClassificationMax(stats.maximumValue)
                layer.renderer().shader().rasterShaderFunction().classifyColorRamp()

    def _load_contrast_enhancement(self, properties: dict) -> None:
        if "algorithm" in properties:
            alg = properties["algorithm"]
            match alg:
                case "StretchToMinimumMaximum":
                    self.contrast_algorithm = (
                        ContrastEnhancementAlgorithm.StretchToMinimumMaximum)
                case "NoEnhancement":
                    self.contrast_algorithm = (
                        ContrastEnhancementAlgorithm.NoEnhancement)

        if "limits_min_max" in properties:
            limits = properties["limits_min_max"]
            match limits:
                case "UserDefined":
                    self.contrast_limits = QgsRasterMinMaxOrigin.Limits.None_
                case "CumulativeCut":
                    self.contrast_limits = QgsRasterMinMaxOrigin.Limits.CumulativeCut
                case "MinMax":
                    self.contrast_limits = QgsRasterMinMaxOrigin.Limits.MinMax
