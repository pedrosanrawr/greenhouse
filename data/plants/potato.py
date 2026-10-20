"""Potato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.generic_yield import GenericYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook (ID 29, Solanum tuberosum): EcoCrop T 7 / 15-25 / 30 C, cycle 90-160 d,
# first harvest 90-160 d (cycle used as a proxy), reference yield 1.0-3.5 kg/m2
# (typical 2.25) of fresh tubers, spacing 25 x 60 cm.
# The workbook flags potato as a cool/highland crop: lowland greenhouse use may
# be infeasible without strong cooling. Everything marked TEST VALUE is provisional.
#
# total_biomass_g derivation (TEST VALUE chain):
#   0.25 m x 0.60 m = 0.15 m2/plant -> 2.25 kg/m2 x 0.15 = 0.34 kg fresh tubers
#   x ~20% dry matter (TEST) = ~67 g dry tubers
#   tuber share of total growth with the ratios below = ~0.63
#   -> ~107 g growth + initial biomass = ~108 g
POTATO_PARAMETERS = CropParameters(
    name="Potato",
    t_base=7.0,
    t_opt=20.0,  # TEST VALUE: midpoint of the supplied 15-25 C optimum band
    t_max=30.0,
    lue=2.3,  # TEST VALUE
    extinction_k=0.75,  # TEST VALUE
    sla=0.022,  # TEST VALUE, m²/g
    maintenance={
        "leaf": 0.010,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.001,  # TEST VALUE
    },
    # Not read by the engine any more; kept because the field is required.
    sink_demand={
        "leaf": 0.12,  # TEST VALUE, g/plant/day
        "stem": 0.06,  # TEST VALUE
        "root": 0.04,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.45,  # TEST VALUE
    },
    biomass_ratio={
        "vegetative": {  # emergence and canopy build-up
            "leaf": 0.50,  # TEST VALUE
            "stem": 0.30,  # TEST VALUE
            "root": 0.20,  # TEST VALUE
        },
        "tuber_initiation": {  # stolon tips start to swell
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.20,  # TEST VALUE
            "root": 0.10,  # TEST VALUE
            "stem_tuber": 0.35,  # TEST VALUE
        },
        "bulking": {  # tubers fill
            "leaf": 0.15,  # TEST VALUE
            "stem": 0.07,  # TEST VALUE
            "root": 0.03,  # TEST VALUE
            "stem_tuber": 0.75,  # TEST VALUE
        },
        "maturation": {  # canopy declining, nearly all growth to tubers
            "leaf": 0.05,  # TEST VALUE
            "stem": 0.03,  # TEST VALUE
            "root": 0.02,  # TEST VALUE
            "stem_tuber": 0.90,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "tuber_initiation": 25,  # TEST VALUE
        "bulking": 45,  # TEST VALUE
        "maturation": 110,  # TEST VALUE
    },
    total_biomass_g=108.0,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 0.5,  # TEST VALUE, g/plant (sprout; seed piece not counted)
        "stem": 0.5,  # TEST VALUE
        "root": 0.2,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.0,
    },
    harvestable_organ="stem_tuber",
    cycle_min_days=90,
    cycle_max_days=160,
    first_harvest_min_days=90,
    first_harvest_max_days=160,
)

POTATO = CropDefinition(
    parameters=POTATO_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
            "clay_loam",
            nutrients=NutrientApplication(100, 60, 60),
            recommended_npk={"potato": (90.0, 45.0, 45.0)},
        ),
    yield_model=GenericYieldModel(),
)