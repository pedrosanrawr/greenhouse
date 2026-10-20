"""Plant definition that binds crop parameters to interchangeable model implementations."""
from dataclasses import dataclass

from data.models.contracts import CropGrowthModel, SoilFertilizerModel, YieldModel
from data.models.types import CropParameters


@dataclass(frozen=True)
class CropDefinition:
    parameters: CropParameters
    growth_model: CropGrowthModel
    soil_model: SoilFertilizerModel
    yield_model: YieldModel

    @property
    def name(self) -> str:
        return self.parameters.name