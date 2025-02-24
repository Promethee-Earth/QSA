from qgis.core import QgsRasterMinMaxOrigin, QgsSingleBandGrayRenderer, QgsRasterShader, QgsColorRampShader, QgsStyle, QgsGradientColorRamp
from .renderer import RasterSymbologyRenderer
from .renderer import ContrastEnhancementAlgorithm

class PropertiesBuilder:

    @staticmethod
    def load_multibandcolor_properties(renderer: RasterSymbologyRenderer, properties: dict) -> None:
        if "red" in properties:
            red = properties["red"]
            renderer.renderer.setRedBand(int(red["band"]))

            if renderer.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in red:
                    renderer.red_min = float(red["min"])

                if "max" in red:
                    renderer.red_max = float(red["max"])

        if "blue" in properties:
            blue = properties["blue"]
            renderer.renderer.setBlueBand(int(blue["band"]))

            if renderer.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in blue:
                    renderer.blue_min = float(blue["min"])
                if "max" in blue:
                    renderer.blue_max = float(blue["max"])

        if "green" in properties:
            green = properties["green"]
            renderer.renderer.setGreenBand(int(green["band"]))

            if renderer.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in green:
                    renderer.green_min = float(green["min"])

                if "max" in green:
                    renderer.green_max = float(green["max"])

    @staticmethod
    def _load_singlebandgray_properties(renderer: RasterSymbologyRenderer, properties: dict) -> None:
        if "gray" in properties:
            gray = properties["gray"]
            renderer.renderer.setGrayBand(int(gray["band"]))

            if renderer.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
                if "min" in gray:
                    renderer.gray_min = float(gray["min"])

                if "max" in gray:
                    renderer.gray_max = float(gray["max"])

        if "color_gradient" in properties:
            gradient = properties["color_gradient"]
            if gradient == "blacktowhite":
                renderer.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.BlackToWhite
                )
            elif gradient == "whitetoblack":
                renderer.renderer.setGradient(
                    QgsSingleBandGrayRenderer.Gradient.WhiteToBlack
                )
    @staticmethod     
    def _load_singlebandpseudocolor_properties(renderer: RasterSymbologyRenderer, properties: dict) -> None:
        # always stretch to min/max in case of the singlepseudocolor renderer
        renderer.contrast_algorithm = (
            ContrastEnhancementAlgorithm.StretchToMinimumMaximum
        )

        band_min = None
        band_max = None
        if "band" in properties:
            band = properties["band"]
            renderer.renderer.setBand(int(band["band"]))

            if renderer.contrast_limits == QgsRasterMinMaxOrigin.Limits.None_:
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
            renderer.renderer.setShader(shader)

            if band_min is not None:
                renderer.renderer.setClassificationMin(band_min)
            if band_max is not None:
                renderer.renderer.setClassificationMax(band_max)

            renderer.renderer.shader().rasterShaderFunction().classifyColorRamp()