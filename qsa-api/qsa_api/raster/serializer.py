from raster import RasterSymbologyRenderer
from qgis.core import QgsRasterLayer, QgsContrastEnhancement, QgsRasterMinMaxOrigin, QgsSingleBandGrayRenderer, QgsColorRampShader
from pathlib import Path


class RasterSerializer:
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
            props = RasterSerializer._multibandcolor_properties(
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
