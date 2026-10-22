"""Radish baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import RootTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 19: EcoCrop T 3 / 12-25 / 30 C, cycle 21-135 d, first harvest 22-50 d.
# Workbook harvestable organ: Swollen hypocotyl/root. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL TEST VALUES cloned from the
# radish archetype. The workbook still flags water/nutrient bands as unverified.

RADISH_PARAMETERS = CropParameters(
    name="Radish",
    t_base=3,  # workbook absolute T min
    t_opt=18.5,  # workbook: midpoint of the supplied optimum band
    t_max=30,  # workbook absolute T max
    t_abs_min=3, t_opt_min=12, t_opt_max=25, t_abs_max=30,  # workbook
    temperature_band_verified=True,
    lue=2.2,  # TEST VALUE
    extinction_k=0.8,  # TEST VALUE
    sla=0.02,  # TEST VALUE, m²/g
    # Workbook: water band 100-437.5 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=100, water_opt_min_mm=200, water_opt_max_mm=350, water_abs_max_mm=437.5,  # workbook
    water_cycle_days=40,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=40, n_rec_max_kg_ha=60,  # workbook
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=60,  # workbook
    k2o_rec_min_kg_ha=50, k2o_rec_max_kg_ha=80,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "root_tuber": 0.001,  # TEST VALUE
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.25,  # TEST VALUE
        "stem": 0.15,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "root_tuber": 0.8,  # TEST VALUE
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.45,  # TEST VALUE
            "stem": 0.35,  # TEST VALUE
            "root": 0.2,  # TEST VALUE
        },
        "tuber_initiation": {
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.25,  # TEST VALUE
            "root": 0.1,  # TEST VALUE
            "root_tuber": 0.3,  # TEST VALUE
        },
        "bulking": {
            "leaf": 0.12,  # TEST VALUE
            "stem": 0.08,  # TEST VALUE
            "root": 0.05,  # TEST VALUE
            "root_tuber": 0.75,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "tuber_initiation": 24,  # TEST VALUE
        "bulking": 47,  # TEST VALUE
    },
    total_biomass_g=35,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.5,  # TEST VALUE, g/plant
        "stem": 2.0,  # TEST VALUE, g/plant
        "root": 0.2,  # TEST VALUE, g/plant
    },
    harvestable_organ="root_tuber",
    cycle_min_days=21, cycle_max_days=135,  # workbook
    first_harvest_min_days=22, first_harvest_max_days=50,  # workbook
)

RADISH = CropDefinition(
    parameters=RADISH_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"radish": (90, 45, 45)},
    ),
    yield_model=RootTuberYieldModel(),
)
