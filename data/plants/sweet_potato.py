"""Sweet potato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.generic_yield import GenericYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook (ID 23, Ipomoea batatas): EcoCrop T 10 / 18-28 / 38 C, cycle 80-170 d,
# first harvest 80-170 d (cycle used as a proxy), reference yield 1.75-2.75 kg/m2
# (typical 2.25) of fresh storage roots, spacing 30 x 90 cm.
# Everything marked TEST VALUE is provisional.
#
# total_biomass_g derivation (TEST VALUE chain):
#   0.30 m x 0.90 m = 0.27 m2/plant -> 2.25 kg/m2 x 0.27 = 0.61 kg fresh roots
#   x ~27% dry matter (TEST) = ~164 g dry roots
#   tuber share of total growth with the ratios below = ~0.54
#   -> ~305 g growth + initial biomass = ~310 g
SWEET_POTATO_PARAMETERS = CropParameters(
    name="Sweet potato",
    t_base=10.0,
    t_opt=23.0,  # TEST VALUE: midpoint of the supplied 18-28 C optimum band
    t_max=38.0,
    lue=2.2,  # TEST VALUE
    extinction_k=0.8,  # TEST VALUE
    sla=0.02,  # TEST VALUE, m²/g
    maintenance={
        "leaf": 0.010,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.001,  # TEST VALUE
        "stem_tuber": 0.0,
    },
    # Not read by the engine any more; kept because the field is required.
    sink_demand={
        "leaf": 0.25,  # TEST VALUE, g/plant/day
        "stem": 0.15,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.80,  # TEST VALUE
        "stem_tuber": 0.0,
    },
    biomass_ratio={
        "vegetative": {  # vine establishment, no storage roots yet
            "leaf": 0.45,  # TEST VALUE
            "stem": 0.35,  # TEST VALUE
            "root": 0.20,  # TEST VALUE
        },
        "tuber_initiation": {  # storage roots begin to form
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.25,  # TEST VALUE
            "root": 0.10,  # TEST VALUE
            "root_tuber": 0.30,  # TEST VALUE
        },
        "bulking": {  # storage roots dominate
            "leaf": 0.12,  # TEST VALUE
            "stem": 0.08,  # TEST VALUE
            "root": 0.05,  # TEST VALUE
            "root_tuber": 0.75,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "tuber_initiation": 30,  # TEST VALUE
        "bulking": 60,  # TEST VALUE
    },
    total_biomass_g=310.0,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.5,  # TEST VALUE, g/plant (vine cutting)
        "stem": 2.0,  # TEST VALUE
        "root": 0.2,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.0,
    },
    harvestable_organ="root_tuber",
    cycle_min_days=80,
    cycle_max_days=170,
    first_harvest_min_days=80,
    first_harvest_max_days=170,
)

SWEET_POTATO = CropDefinition(
    parameters=SWEET_POTATO_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
            "clay_loam",
            nutrients=NutrientApplication(100, 60, 60),
            recommended_npk={"sweet_potato": (90.0, 45.0, 45.0)},
        ),
    yield_model=GenericYieldModel(),
)