"""Generic harvestable-biomass estimate for the initial baseline."""
from data.models.contracts import YieldModel
from data.models.types import CropParameters, CropState, YieldState


class GenericYieldModel(YieldModel):
    """Treats the configured harvestable organ as a yield proxy after harvest age.

    No harvest event is simulated, and biomass remains on the plant. The result
    is therefore an estimated harvestable biomass, not cumulative harvested yield.
    """

    def estimate_yield(
        self, crop: CropParameters, state: CropState, day_index: int
    ) -> YieldState:
        age = day_index + 1
        ready = age >= crop.first_harvest_min_days
        harvestable = (
            max(0.0, state.biomass_g.get(crop.harvestable_organ, 0.0)) if ready else 0.0
        )
        return YieldState(harvestable_biomass_g=harvestable, yield_ready=ready)
