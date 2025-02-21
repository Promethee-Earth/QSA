# coding: utf8

from enum import Enum
from pathlib import Path
from wrappers import Result, Err

from qgis.core import (
    QgsStyle,
    QgsRasterLayer,
    QgsRasterShader,
    QgsColorRampShader,
    QgsRasterBandStats,
    QgsGradientColorRamp,
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
        if (
            self.renderer.type()
            == RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY.value
        ):
            return RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY
        elif (
            self.renderer.type()
            == RasterSymbologyRenderer.Type.MULTI_BAND_COLOR.value
        ):
            return RasterSymbologyRenderer.Type.MULTI_BAND_COLOR
        elif (
            self.renderer.type()
            == RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR.value
        ):
            return RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR

        return None

    def load(self, properties: dict) -> (bool, str):
        if not self.renderer:
            return False, "Invalid renderer"

        if "contrast_enhancement" in properties:
            self._load_contrast_enhancement(properties["contrast_enhancement"])

        if self.type == RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
            self._load_multibandcolor_properties(properties)
        elif self.type == RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
            self._load_singlebandgray_properties(properties)
        elif self.type == RasterSymbologyRenderer.Type.SINGLE_BAND_PSEUDOCOLOR:
            self._load_singlebandpseudocolor_properties(properties)

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
            case QgsRasterMinMaxOrigin.Limits.CumulativeCut:
                self.__set_cumulative_cut_min_max(
                    raster, QgsRasterMinMaxOrigin.CUMULATIVE_CUT_UPPER, QgsRasterMinMaxOrigin.CUMULATIVE_CUT_LOWER)
            # default min/max
            case QgsRasterMinMaxOrigin.Limits.MinMax:
                pass

    def __set_user_defined_min_max(self, raster: QgsRasterLayer):
        match self.type:
            case RasterSymbologyRenderer.Type.SINGLE_BAND_GRAY:
                ce = QgsContrastEnhancement(
                    raster.renderer().contrastEnhancement())
                self.__set_min_max(ce, raster, self.Color.GRAY)
            case RasterSymbologyRenderer.Type.MULTI_BAND_COLOR:
                # red
                red_ce = QgsContrastEnhancement(
                    raster.renderer().redContrastEnhancement())
                self.__set_min_max(red_ce, raster, self.Color.RED)
                # green
                green_ce = QgsContrastEnhancement(
                    raster.renderer().greenContrastEnhancement())
                self.__set_min_max(green_ce, raster, self.Color.GREEN)
                # blue
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

    @staticmethod
    def style_to_json(path: Path) -> (dict, str):
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

    def _refresh_min_max_multibandcolor(self, layer: QgsRasterLayer) -> None:
        renderer = layer.renderer()
        red_ce = QgsContrastEnhancement(renderer.redContrastEnhancement())
        green_ce = QgsContrastEnhancement(renderer.greenContrastEnhancement())
        blue_ce = QgsContrastEnhancement(renderer.blueContrastEnhancement())

        # early break
        alg = red_ce.contrastEnhancementAlgorithm()
        if (
            alg == ContrastEnhancementAlgorithm.NoEnhancement
            or alg == ContrastEnhancementAlgorithm.UserDefinedEnhancement
        ):
            return

        # compute min/max with "Accuracy: estimate"
        min_max_origin = renderer.minMaxOrigin().limits()
        if min_max_origin == QgsRasterMinMaxOrigin.Limits.MinMax:
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

    def _load_multibandcolor_properties(self, properties: dict) -> None:
        if "red" in properties:
            red = properties["red"]
            self.renderer.setRedBand(int(red["band"]))

            if self.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in red:
                    self.red_min = float(red["min"])

                if "max" in red:
                    self.red_max = float(red["max"])

        if "blue" in properties:
            blue = properties["blue"]
            self.renderer.setBlueBand(int(blue["band"]))

            if self.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in blue:
                    self.blue_min = float(blue["min"])

                if "max" in blue:
                    self.blue_max = float(blue["max"])

        if "green" in properties:
            green = properties["green"]
            self.renderer.setGreenBand(int(green["band"]))

            if self.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in green:
                    self.green_min = float(green["min"])

                if "max" in green:
                    self.green_max = float(green["max"])

    def _load_singlebandgray_properties(self, properties: dict) -> None:
        if "gray" in properties:
            gray = properties["gray"]
            self.renderer.setGrayBand(int(gray["band"]))

            if self.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in gray:
                    self.gray_min = float(gray["min"])

                if "max" in gray:
                    self.gray_max = float(gray["max"])

        if "color_gradient" in properties:
            gradient = properties["color_gradient"]
            if gradient == "blacktowhite":
                self.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.BlackToWhite
                )
            elif gradient == "whitetoblack":
                self.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.WhiteToBlack
                )

    def _load_singlebandpseudocolor_properties(self, properties: dict) -> None:
        # always stretch to min/max in case of the singlepseudocolor renderer
        self.contrast_algorithm = (
            ContrastEnhancementAlgorithm.StretchToMinimumMaximum
        )

        band_min = None
        band_max = None
        if "band" in properties:
            band = properties["band"]
            self.renderer.setBand(int(band["band"]))

            if self.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in band:
                    band_min = float(band["min"])

                if "max" in band:
                    band_max = float(band["max"])

        if "ramp" in properties:
            ramp = properties["ramp"]
            shader_type = QgsColorRampShader.Type.Interpolated
            if "interpolation" in ramp:
                interpolation = ramp["interpolation"]
                if interpolation == "Discrete":
                    shader_type = QgsColorRampShader.Type.Discrete
                elif interpolation == "Exact":
                    shader_type = QgsColorRampShader.Type.Exact

            color_ramp = QgsStyle().defaultStyle().colorRamp("Spectral")
            if "name" in ramp and ramp["name"]:
                color_ramp = QgsStyle().defaultStyle().colorRamp(ramp["name"])
            elif "color1" in ramp and "color2" in ramp:
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
        if "algorithm" in properties:
            alg = properties["algorithm"]
            if alg == "StretchToMinimumMaximum":
                self.contrast_algorithm = (
                    ContrastEnhancementAlgorithm.StretchToMinimumMaximum
                )
            elif alg == "NoEnhancement":
                self.contrast_algorithm = (
                    ContrastEnhancementAlgorithm.NoEnhancement
                )

        if "limits_min_max" in properties:
            limits = properties["limits_min_max"]
            if limits == "UserDefined":
                self.contrast_limits = QgsRasterMinMaxOrigin.Limits.None_
            elif limits == "MinMax":
                self.contrast_limits = QgsRasterMinMaxOrigin.Limits.MinMax
