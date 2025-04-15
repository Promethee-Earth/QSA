# coding: utf8

import sys
from enum import Enum
from pathlib import Path

from qgis.core import (
    QgsColorRampShader,
    QgsContrastEnhancement,
    QgsGradientColorRamp,
    QgsMultiBandColorRenderer,
    QgsRasterBandStats,
    QgsRasterLayer,
    QgsRasterMinMaxOrigin,
    QgsRasterShader,
    QgsSingleBandGrayRenderer,
    QgsSingleBandPseudoColorRenderer,
    QgsStyle,
)

from .min_max import MinMax, MultiBand, SignleBand
from ..utils import logger

ContrastEnhancementAlgorithm = (
    QgsContrastEnhancement.ContrastEnhancementAlgorithm)


class RasterMultiBandStats:
    red_band: QgsRasterBandStats
    green_band: QgsRasterBandStats
    blue_band: QgsRasterBandStats

    def __init__(self, layer: QgsRasterLayer):
        renderer: QgsMultiBandColorRenderer = layer.renderer()
        self.red_band = layer.dataProvider().bandStatistics(
            renderer.redBand(),
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        self.green_band = layer.dataProvider().bandStatistics(
            renderer.greenBand(),
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        self.blue_band = layer.dataProvider().bandStatistics(
            renderer.blueBand(),
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )


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

        self.cumulative_cut_upper = None
        self.cumulative_cut_lower = None

        match name:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY.value:
                self.renderer = QgsSingleBandGrayRenderer(None, 1)
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR.value:
                self.renderer = QgsMultiBandColorRenderer(None, 1, 1, 1)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR.value:
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
        """init renderer with request properties"""
        if not self.renderer:
            return False, "Invalid renderer"
        if "contrast_enhancement" in properties:
            self.__debug("Load contrast enhancement")
            self._load_contrast_enhancement(properties["contrast_enhancement"])
            match self.type:
                case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                    self.__debug("Load multibandcolor properties")
                    self._load_multibandcolor_properties(properties)
                case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                    self.__debug("Load singlebandgray properties")
                    self._load_singlebandgray_properties(properties)
                case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
                    self.__debug("Load singlebandpseudocolor properties")
                    self._load_singlebandpseudocolor_properties(properties)
        return True, ""

    def process_renderering(self, raster: QgsRasterLayer, rendering: dict) -> None:
        """Apply rendering to the template raster"""
        # config rendering
        if self.contrast_algorithm == ContrastEnhancementAlgorithm.NoEnhancement:
            self.__debug("No rendering needed")
            return
        mapping = {
            "gamma": lambda v: raster.brightnessFilter().setGamma(float(v)),
            "brightness": lambda v: raster.brightnessFilter().setBrightness(int(v)),
            "contrast": lambda v: raster.brightnessFilter().setContrast(int(v)),
            "saturation": lambda v: raster.hueSaturationFilter().setSaturation(int(v)),
        }
        for key, action in mapping.items():
            if key in rendering:
                action(rendering[key])

    def set_contrast_enhancement(self, raster: QgsRasterLayer) -> None:
        match self.contrast_algorithm:
            case ContrastEnhancementAlgorithm.StretchToMinimumMaximum:
                self.__debug("Stretch to min/max")
                raster.setContrastEnhancement(
                    self.contrast_algorithm, self.contrast_limits)
                match self.contrast_limits:
                    case QgsRasterMinMaxOrigin.Limits.None_:
                        self.set_user_defined_limits(raster)
                    case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                        self.set_cumulative_cut_limits(raster)
            case ContrastEnhancementAlgorithm.NoEnhancement:
                self.__debug("No enhancement")
                raster.setContrastEnhancement(self.contrast_algorithm)

    def set_user_defined_limits(self, raster: QgsRasterLayer) -> None:
        """Set user defined limits to the template raster"""
        self.__debug("Set user defined limits")
        match self.type:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                ce = QgsContrastEnhancement(
                    raster.renderer().contrastEnhancement())
                self._set_min_max(raster, ce, self.Color.GRAY)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
                return
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                red_ce = QgsContrastEnhancement(
                    raster.renderer().redContrastEnhancement())
                self._set_min_max(raster, red_ce, self.Color.RED)

                green_ce = QgsContrastEnhancement(
                    raster.renderer().greenContrastEnhancement())
                self._set_min_max(
                    raster, green_ce, self.Color.GREEN)

                blue_ce = QgsContrastEnhancement(
                    raster.renderer().blueContrastEnhancement())
                self._set_min_max(
                    raster, blue_ce, self.Color.BLUE)

    def set_cumulative_cut_limits(self, raster: QgsRasterLayer) -> None:
        """Set cumulative cut limits to the template raster"""
        self.__debug("Set cumulative cut limits")
        min_max_cut = QgsRasterMinMaxOrigin()
        min_max_cut.setLimits(QgsRasterMinMaxOrigin.Limits.CumulativeCut)
        min_max_cut.setCumulativeCutUpper(self.cumulative_cut_upper)
        min_max_cut.setCumulativeCutLower(self.cumulative_cut_lower)
        raster.renderer().setMinMaxOrigin(min_max_cut)

    def refresh_min_max(self, layer: QgsRasterLayer) -> MinMax:
        min_max = None
        match self.type:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                self.__debug("Refresh min/max for singlebandgray")
                min_max = self._refresh_min_max_singlebandgray(layer)
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                self.__debug("Refresh min/max for multibandcolor")
                min_max = self._refresh_min_max_multibandcolor(layer)
            case RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
                self.__debug("Refresh min/max for singlebandpseudocolor")
                min_max = self._refresh_min_max_singlebandpseudocolor(layer)
        return min_max

    # private methods ######################################################################################################
    def _set_min_max(self, layer: QgsRasterLayer, ce: QgsContrastEnhancement, color: Color) -> None:
        match color:
            case RasterSymbologyRenderer.Color.GRAY:
                if self.gray_min is not None:
                    ce.setMinimumValue(self.gray_min)
                if self.gray_max is not None:
                    ce.setMaximumValue(self.gray_max)
                layer.renderer().setContrastEnhancement(ce)
            case RasterSymbologyRenderer.Color.RED:
                if self.red_min is not None:
                    ce.setMinimumValue(self.red_min)
                if self.red_max is not None:
                    ce.setMaximumValue(self.red_max)
                layer.renderer().setRedContrastEnhancement(ce)
            case RasterSymbologyRenderer.Color.GREEN:
                if self.green_min is not None:
                    ce.setMinimumValue(self.green_min)
                if self.green_max is not None:
                    ce.setMaximumValue(self.green_max)
                layer.renderer().setGreenContrastEnhancement(ce)
            case RasterSymbologyRenderer.Color.BLUE:
                if self.blue_min is not None:
                    ce.setMinimumValue(self.blue_min)
                if self.blue_max is not None:
                    ce.setMaximumValue(self.blue_max)
                layer.renderer().setBlueContrastEnhancement(ce)

    def _refresh_min_max_multibandcolor(self, layer: QgsRasterLayer) -> MinMax:
        renderer: QgsMultiBandColorRenderer = layer.renderer()
        limits = renderer.minMaxOrigin().limits()
        red_ce = QgsContrastEnhancement(renderer.redContrastEnhancement())
        green_ce = QgsContrastEnhancement(renderer.greenContrastEnhancement())
        blue_ce = QgsContrastEnhancement(renderer.blueContrastEnhancement())
        alg = red_ce.contrastEnhancementAlgorithm()
        self.__debug(f"contrast enhancement algorithm: {alg}")
        self.__debug(f"limits: {limits}")
        red_band = renderer.redBand()
        green_band = renderer.greenBand()
        blue_band = renderer.blueBand()

        result = MultiBand()
        red_stat = layer.dataProvider().bandStatistics(red_band, QgsRasterBandStats.All,
                                                       layer.extent(), 250000)
        green_stat = layer.dataProvider().bandStatistics(green_band, QgsRasterBandStats.All,
                                                         layer.extent(), 250000)
        blue_stat = layer.dataProvider().bandStatistics(blue_band, QgsRasterBandStats.All,
                                                        layer.extent(), 250000)

        if alg == ContrastEnhancementAlgorithm.NoEnhancement:
            self.__debug("No min/max refresh needed")
            layer.dataProvider().setNoDataValue(red_band, 0)
            layer.dataProvider().setNoDataValue(green_band, 0)
            layer.dataProvider().setNoDataValue(blue_band, 0)
            return result

        match limits:
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                self.__debug("compute min/max for multibandcolor")

                red_ce.setMinimumValue(red_stat.minimumValue)
                red_ce.setMaximumValue(red_stat.maximumValue)
                result.set_red_band(red_ce.minimumValue, red_ce.maximumValue)

                green_ce.setMinimumValue(green_stat.minimumValue)
                green_ce.setMaximumValue(green_stat.maximumValue)
                result.set_green_band(green_ce.minimumValue, green_ce.maximumValue)

                blue_ce.setMinimumValue(blue_stat.minimumValue)
                blue_ce.setMaximumValue(blue_stat.maximumValue)
                result.set_blue_band(blue_ce.minimumValue, blue_ce.maximumValue)

            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__debug("compute cumulative cut for multibandcolor")
                self.__debug(f"")

                red_min_max = self._compute_cumulative_cut(layer, red_band)
                red_ce.setMinimumValue(red_min_max[0])
                red_ce.setMaximumValue(red_min_max[1])
                result.set_red_band(red_min_max[0], red_min_max[1])

                green_min_max = self._compute_cumulative_cut(layer, green_band)
                green_ce.setMinimumValue(green_min_max[0])
                green_ce.setMaximumValue(green_min_max[1])
                result.set_green_band(green_min_max[0], green_min_max[1])

                blue_min_max = self._compute_cumulative_cut(layer, blue_band)
                blue_ce.setMinimumValue(blue_min_max[0])
                blue_ce.setMaximumValue(blue_min_max[1])
                result.set_blue_band(blue_min_max[0], blue_min_max[1])

            case QgsRasterMinMaxOrigin.Limits.None_:
                self.__debug("No min/max refresh needed")
                result.set_red_band(red_ce.minimumValue(), red_ce.maximumValue())
                result.set_green_band(green_ce.minimumValue(), green_ce.maximumValue())
                result.set_blue_band(blue_ce.minimumValue(), blue_ce.maximumValue())
                return result

        layer.renderer().setRedContrastEnhancement(red_ce)
        layer.renderer().setGreenContrastEnhancement(green_ce)
        layer.renderer().setBlueContrastEnhancement(blue_ce)

        return result

    def _refresh_min_max_singlebandgray(self, layer: QgsRasterLayer) -> MinMax:
        ce = QgsContrastEnhancement(layer.renderer().contrastEnhancement())
        alg = ce.contrastEnhancementAlgorithm()
        limits = layer.renderer().minMaxOrigin().limits()
        self.__debug(f"contrast enhancement algorithm: {alg}")
        self.__debug(f"limits: {limits}")

        result = SignleBand()
        stats = layer.dataProvider().bandStatistics(
            1,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        result.set_band(stats.minimumValue, stats.maximumValue)

        if alg == ContrastEnhancementAlgorithm.NoEnhancement:
            self.__debug("No min/max refresh needed")
            layer.setProperty("contrast_enhancement", "NoEnhancement")
            return result

        match layer.renderer().minMaxOrigin().limits():
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                self.__debug("compute min/max for singlebandgray")
                ce.setMinimumValue(stats.minimumValue)
                ce.setMaximumValue(stats.maximumValue)
                result.set_band(stats.minimumValue, stats.maximumValue)
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__debug("compute cumulative cut for singlebandgray")
                min_max = self._compute_cumulative_cut(layer)
                ce.setMinimumValue(min_max[0])
                ce.setMaximumValue(min_max[1])
                result.set_band(min_max[0], min_max[1])
            case QgsRasterMinMaxOrigin.Limits.None_:
                self.__debug("No min/max refresh needed")
                result.set_band(ce.minimumValue(), ce.maximumValue())
                return result
        layer.renderer().setContrastEnhancement(ce)
        return result

    def _refresh_min_max_singlebandpseudocolor(self, layer: QgsRasterLayer) -> MinMax:
        limits = layer.renderer().minMaxOrigin().limits()
        self.__debug(f"limits: {limits}")
        layer.dataProvider().setNoDataValue(1, 0)
        stats = layer.dataProvider().bandStatistics(
            1,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )
        result = SignleBand()
        result.set_band(stats.minimumValue, stats.maximumValue)

        match limits:
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                self.__debug("compute min/max for singlebandpseudocolor")
                layer.renderer().setClassificationMin(stats.minimumValue)
                layer.renderer().setClassificationMax(stats.maximumValue)
                layer.renderer().shader().rasterShaderFunction().classifyColorRamp()
                result.set_band(stats.minimumValue, stats.maximumValue)
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__debug(
                    "compute cumulative cut for singlebandpseudocolor")
                min_max = self._compute_cumulative_cut(layer)
                layer.renderer().setClassificationMin(min_max[0])
                layer.renderer().setClassificationMax(min_max[1])
                layer.renderer().shader().rasterShaderFunction().classifyColorRamp()
                result.set_band(min_max[0], min_max[1])
            case QgsRasterMinMaxOrigin.Limits.None_:
                self.__debug("No min/max refresh needed")
        return result

    def _compute_cumulative_cut(self, layer: QgsRasterLayer, band: int = 1) -> (float , float):
        min_max_origin = layer.renderer().minMaxOrigin()
        values = layer.dataProvider().bandStatistics(
            band,
            QgsRasterBandStats.Min | QgsRasterBandStats.Max,
            layer.extent(),
            250000,
        )

        cut_min = min_max_origin.cumulativeCutLower()
        cut_max = min_max_origin.cumulativeCutUpper()

        cut_min_max = layer.dataProvider().cumulativeCut(
            band, cut_min, cut_max, layer.extent())

        self.__debug(
            f"min: {values.minimumValue}, max: {values.maximumValue}, cut_min: {cut_min}, cut_max: {cut_max}")
        self.__debug(
            f"cumulative cut min: {cut_min_max[0]}, cumulative cut max: {cut_min_max[1]}")

        return cut_min_max

    def _load_multibandcolor_properties(self, properties: dict) -> None:
        if "red" in properties:
            red = properties["red"]
            self.renderer.setRedBand(int(red["band"]))
        if "blue" in properties:
            blue = properties["blue"]
            self.renderer.setBlueBand(int(blue["band"]))
        if "green" in properties:
            green = properties["green"]
            self.renderer.setGreenBand(int(green["band"]))
        match self.contrast_limits:
            case QgsRasterMinMaxOrigin.Limits.None_:
                self.red_min = float(red["min"]) if red["min"] else None
                self.red_max = float(red["max"]) if red["max"] else None
                self.blue_min = float(blue["min"]) if blue["min"] else None
                self.blue_max = float(blue["max"]) if blue["max"] else None
                self.green_min = float(green["min"]) if green["min"] else None
                self.green_max = float(green["max"]) if green["max"] else None

    def _load_singlebandgray_properties(self, properties: dict) -> None:
        if "gray" in properties:
            gray = properties["gray"]
            self.renderer.setGrayBand(int(gray["band"]))
            match self.contrast_limits:
                case QgsRasterMinMaxOrigin.Limits.None_:
                    self.gray_min = float(gray["min"]) if gray["min"] else None
                    self.gray_max = float(gray["max"]) if gray["max"] else None

        if "color_gradient" in properties:
            gradient = properties["color_gradient"]
            if gradient == "blacktowhite":
                self.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.BlackToWhite)
            elif gradient == "whitetoblack":
                self.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.WhiteToBlack)

    def _load_singlebandpseudocolor_properties(self, properties: dict) -> None:
        # always stretch to min/max in case of the singlepseudocolor renderer
        self.contrast_algorithm = (
            ContrastEnhancementAlgorithm.StretchToMinimumMaximum)
        band_min = None
        band_max = None
        if "band" in properties:
            band = properties["band"]
            self.renderer.setBand(int(band["band"]))

            match self.contrast_limits:
                case QgsRasterMinMaxOrigin.Limits.None_:
                    band_min = float(band["min"]) if band["min"] else None
                    band_max = float(band["max"]) if band["max"] else None

        if "ramp" in properties:
            ramp = properties["ramp"]
            shader_type = QgsColorRampShader.Type.Interpolated
            match ramp["interpolation"]:
                case "Discrete":
                    shader_type = QgsColorRampShader.Type.Discrete
                case "Exact":
                    shader_type = QgsColorRampShader.Type.Exact
                case None:
                    pass

            color_ramp = QgsStyle().defaultStyle().colorRamp("Spectral")
            if "name" in ramp:
                color_ramp = QgsStyle().defaultStyle().colorRamp(ramp["name"])
            if "color1" in ramp and "color2" in ramp:
                color_ramp = QgsGradientColorRamp.create(ramp)

            ramp_shader = QgsColorRampShader()
            ramp_shader.setSourceColorRamp(color_ramp)
            ramp_shader.setColorRampType(shader_type)

            shader = QgsRasterShader()
            shader.setRasterShaderFunction(ramp_shader)
            self.renderer.setShader(shader)

            if band_min is not None:
                self.renderer.setClassificationMin(band_min)
            if band_max is not None:
                self.renderer.setClassificationMax(band_max)

            self.renderer.shader().rasterShaderFunction().classifyColorRamp()

    def _load_contrast_enhancement(self, properties: dict) -> None:
        alg = properties["algorithm"] if properties["algorithm"] else None
        match alg:
            case "StretchToMinimumMaximum":
                self.contrast_algorithm = ContrastEnhancementAlgorithm.StretchToMinimumMaximum
            case "NoEnhancement":
                self.contrast_algorithm = (
                    ContrastEnhancementAlgorithm.NoEnhancement)
        limits = properties["limits_min_max"] if properties["limits_min_max"] else None
        match limits:
            case "UserDefined":
                self.contrast_limits = QgsRasterMinMaxOrigin.Limits.None_
            case "MinMax":
                self.contrast_limits = QgsRasterMinMaxOrigin.Limits.MinMax
            case "CumulativeCut":
                self.contrast_limits = QgsRasterMinMaxOrigin.Limits.CumulativeCut
                self._load_cumulative_cut(properties)
        self.__debug(
            f"contrast enhancement algorithm: {self.contrast_algorithm}")
        self.__debug(f"limits: {self.contrast_limits}")

    def _load_cumulative_cut(self, properties: dict) -> None:
        if "cumulative_cut_upper" in properties:
            self.cumulative_cut_upper = float(
                (100 - properties["cumulative_cut_upper"]) / 100)
            self.__debug(f"cumulative cut upper: {self.cumulative_cut_upper}")
        if "cumulative_cut_lower" in properties:
            self.cumulative_cut_lower = float(
                (0 + properties["cumulative_cut_lower"]) / 100)
            self.__debug(f"cumulative cut lower: {self.cumulative_cut_lower}")

    def __debug(self, msg: str) -> None:
        caller = f"{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}"
        msg = f"[{caller}][{self.type.value}] {msg}"
        logger().debug(msg)

    # serializer methods ###################################################################################################
    @staticmethod
    def style_to_json(path: Path) -> (dict | str):
        tif = Path(__file__).resolve().parent / "empty.tif"
        rl = QgsRasterLayer(tif.as_posix(), "", "gdal")
        rl.loadNamedStyle(path.as_posix())

        renderer = rl.renderer()
        renderer_type = RasterSymbologyRenderer(renderer.type()).type

        m = {}
        m["name"] = path.stem
        m["type"] = "raster"
        m["symbology"] = {}
        m["symbology"]["type"] = renderer.type()

        props = {}
        if renderer_type == RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
            props = RasterSymbologyRenderer._singlebandgray_properties(
                renderer
            )
        elif renderer_type == RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
            props = RasterSymbologyRenderer._multibandcolor_properties(
                renderer
            )
        elif (
                renderer_type
                == RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR
        ):
            props = RasterSymbologyRenderer._singlebandpseudocolor_properties(
                renderer
            )

        m["symbology"]["properties"] = props

        m["rendering"] = {}
        m["rendering"]["brightness"] = rl.brightnessFilter().brightness()
        m["rendering"]["contrast"] = rl.brightnessFilter().contrast()
        m["rendering"]["gamma"] = rl.brightnessFilter().gamma()
        m["rendering"]["saturation"] = rl.hueSaturationFilter().saturation()

        return m, ""

    @staticmethod
    def _multibandcolor_properties(renderer) -> dict:
        props = {}

        # limits
        limits = renderer.minMaxOrigin().limits()

        props["contrast_enhancement"] = {}
        props["contrast_enhancement"]["limits_min_max"] = "UserDefined"
        if limits == QgsRasterMinMaxOrigin.Limits.MinMax:
            props["contrast_enhancement"]["limits_min_max"] = "MinMax"

        # bands
        props["red"] = {}
        props["red"]["band"] = renderer.redBand()

        props["blue"] = {}
        props["blue"]["band"] = renderer.blueBand()

        props["green"] = {}
        props["green"]["band"] = renderer.greenBand()

        # red band
        if renderer.redContrastEnhancement():
            red_ce = QgsContrastEnhancement(renderer.redContrastEnhancement())

            props["red"]["min"] = red_ce.minimumValue()
            props["red"]["max"] = red_ce.maximumValue()

            # blue band
            blue_ce = QgsContrastEnhancement(
                renderer.blueContrastEnhancement()
            )

            props["blue"]["min"] = blue_ce.minimumValue()
            props["blue"]["max"] = blue_ce.maximumValue()

            # green band
            green_ce = QgsContrastEnhancement(
                renderer.greenContrastEnhancement()
            )

            props["green"]["min"] = green_ce.minimumValue()
            props["green"]["max"] = green_ce.maximumValue()

            # ce
            alg = red_ce.contrastEnhancementAlgorithm()
            props["contrast_enhancement"]["algorithm"] = "NoEnhancement"
            if (
                    alg
                    == QgsContrastEnhancement.ContrastEnhancementAlgorithm.StretchToMinimumMaximum
            ):
                props["contrast_enhancement"][
                    "algorithm"
                ] = "StretchToMinimumMaximum"
        else:
            # default behavior
            props["contrast_enhancement"][
                "algorithm"
            ] = "StretchToMinimumMaximum"

        return props

    @staticmethod
    def _singlebandgray_properties(renderer) -> dict:
        props = {}

        props["gray"] = {}
        props["gray"]["band"] = renderer.grayBand()

        ce = renderer.contrastEnhancement()
        props["gray"]["min"] = ce.minimumValue()
        props["gray"]["max"] = ce.maximumValue()

        gradient = renderer.gradient()
        if gradient == QgsSingleBandGrayRenderer.Gradient.BlackToWhite:
            props["color_gradient"] = "BlackToWhite"
        else:
            props["color_gradient"] = "WhiteToBlack"

        props["contrast_enhancement"] = {}

        alg = ce.contrastEnhancementAlgorithm()
        props["contrast_enhancement"]["algorithm"] = "NoEnhancement"
        if (
                alg
                == QgsContrastEnhancement.ContrastEnhancementAlgorithm.StretchToMinimumMaximum
        ):
            props["contrast_enhancement"][
                "algorithm"
            ] = "StretchToMinimumMaximum"

        limits = renderer.minMaxOrigin().limits()
        props["contrast_enhancement"]["limits_min_max"] = "UserDefined"
        if limits == QgsRasterMinMaxOrigin.Limits.MinMax:
            props["contrast_enhancement"]["limits_min_max"] = "MinMax"

        return props

    @staticmethod
    def _singlebandpseudocolor_properties(renderer) -> dict:
        props = {}

        if renderer.shader() is None:
            return {}, "Invalid shader in singlebandpseudocolor renderer"

        if renderer.shader().rasterShaderFunction().sourceColorRamp() is None:
            return {}, "Invalid color ramp in singlebandpseudocolor renderer"

        props["band"] = {}
        props["band"]["band"] = renderer.band()

        props["band"]["min"] = renderer.classificationMin()
        props["band"]["max"] = renderer.classificationMax()

        props["ramp"] = {}
        shader_fct = renderer.shader().rasterShaderFunction()
        color_1 = (
            shader_fct.sourceColorRamp().properties()["color1"].split("rgb")[0]
        )
        color_2 = (
            shader_fct.sourceColorRamp().properties()["color2"].split("rgb")[0]
        )
        stops = shader_fct.sourceColorRamp().properties()["stops"]
        props["ramp"]["color1"] = color_1
        props["ramp"]["color2"] = color_2
        props["ramp"]["stops"] = stops

        ramp_type = shader_fct.colorRampType()
        if ramp_type == QgsColorRampShader.Discrete:
            props["ramp"]["interpolation"] = "Discrete"
        elif ramp_type == QgsColorRampShader.Exact:
            props["ramp"]["interpolation"] = "Exact"
        elif ramp_type == QgsColorRampShader.Interpolated:
            props["ramp"]["interpolation"] = "Interpolated"

        props["contrast_enhancement"] = {}

        limits = renderer.minMaxOrigin().limits()
        props["contrast_enhancement"]["limits_min_max"] = "UserDefined"
        if limits == QgsRasterMinMaxOrigin.Limits.MinMax:
            props["contrast_enhancement"]["limits_min_max"] = "MinMax"

        return props
