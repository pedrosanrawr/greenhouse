"""Tomato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.generic_soil import GenericSoilFertilizerModel
from data.models.generic_yield import GenericYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Temperature boundaries and broad timing ranges are based on the supplied
# greenhouse crop spreadsheet. The 24 C optimum is a TEST VALUE midpoint.
# Remaining coefficients and biomass values are provisional TEST VALUES.
TOMATO_PARAMETERS = CropParameters(
    name="Tomato",
    t_base=7.0,
    t_opt=24.0,  # TEST VALUE: midpoint of the supplied 20–27 C optimum band
    t_max=35.0,
    lue=2.5,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.03,  # TEST VALUE, m²/g
    maintenance={
        "leaf": 0.010,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.004,  # TEST VALUE
        "fruit": 0.002,  # TEST VALUE
    },
    sink_demand={
        "leaf": 0.20,  # TEST VALUE, g/plant/day
        "stem": 0.10,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.02,  # TEST VALUE
        "fruit": 0.25,  # TEST VALUE
    },
    initial_biomass={
        "leaf": 1.0,  # TEST VALUE, g/plant
        "stem": 0.5,  # TEST VALUE
        "root": 0.3,  # TEST VALUE
        "flower": 0.0,  # TEST VALUE
        "fruit": 0.0,  # TEST VALUE
    },
    harvestable_organ="fruit",
    cycle_min_days=70,
    cycle_max_days=150,
    first_harvest_min_days=70,
    first_harvest_max_days=130,
)

TOMATO = CropDefinition(
    parameters=TOMATO_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=GenericSoilFertilizerModel(),
    yield_model=GenericYieldModel(),
)