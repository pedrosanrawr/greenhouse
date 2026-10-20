"""Generic soil/fertilizer fallback based on user-provided limitation factors."""
from data.models.contracts import SoilFertilizerModel
from data.models.types import CropParameters, GreenhouseConfig, ResourceAvailability


class GenericSoilFertilizerModel(SoilFertilizerModel):
    """Passes configured water/nutrient factors through unchanged.

    This is a placeholder resource model: it does not simulate soil pools,
    fertilizer dissolution, nutrient uptake, or depletion over time.
    """

    def initialize(self, greenhouse: GreenhouseConfig) -> None:
        return None

    def resources_for_day(
        self,
        crop: CropParameters,
        greenhouse: GreenhouseConfig,
        day_index: int,
    ) -> ResourceAvailability:
        return ResourceAvailability(
            water_factor=max(0.0, min(1.0, greenhouse.water_factor)),
            nutrient_factor=max(0.0, min(1.0, greenhouse.nutrient_factor)),
        )