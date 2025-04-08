from abc import ABCMeta, abstractmethod
from enum import Enum

from qgis.core import QgsRasterBandStats

class RasterType(Enum):
    NONE = 0
    SINGLE_BAND = 1
    MULTI_BAND = 2


class Band:
    min: float
    max: float


class MinMax(metaclass=ABCMeta):
    type: RasterType

    def __init__(self, type: RasterType):
        self.type = type

    @staticmethod
    def create(self, type: RasterType):
        match type:
            case RasterType.SINGLE_BAND:
                return SignleBand()
            case RasterType.MULTI_BAND:
                return MultiBand()
            case RasterType.NONE:
                return MinMax(RasterType.NONE)
                
    @abstractmethod
    def serialize(self):
        """Serialize data to JSON"""

@MinMax.register
class SignleBand(MinMax):
    band: Band

    def __init__(self):
        super().__init__(RasterType.SINGLE_BAND)
        self.band = Band()

    def set_band(self, min, max):
        self.band.min = min
        self.band.max = max

    def serialize(self):
        return {
            "band": {
                "min": self.band.min,
                "max": self.band.max
            }
        }


@MinMax.register
class MultiBand(MinMax):
    red_band: Band
    blue_band: Band
    green_band: Band

    def __init__(self):
        super().__init__(RasterType.MULTI_BAND)
        self.red_band = Band()
        self.blue_band = Band()
        self.green_band = Band()

    def set_red_band(self, min, max):
        self.red_band.min = min
        self.red_band.max = max

    def set_blue_band(self, min, max):
        self.blue_band.min = min
        self.blue_band.max = max

    def set_green_band(self, min, max):
        self.green_band.min = min
        self.green_band.max = max

    def serialize(self):
        return {
            "red": {
                "min": self.red_band.min,
                "max": self.red_band.max
            },
            "blue": {
                "min": self.blue_band.min,
                "max": self.blue_band.max
            },
            "green": {
                "min": self.green_band.min,
                "max": self.green_band.max
            }
        }
