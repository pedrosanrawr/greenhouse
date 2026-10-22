"""Onion baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import StemTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 21: EcoCrop T 4 / 12-25 / 30 C, cycle 85-175 d, first harvest 85-175 d.
# Workbook harvestable organ: Bulb. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL TEST VALUES cloned from the
# onion archetype. The workbook still flags water/nutrient bands as unverified.

ONION_PARAMETERS = CropParameters(
    name="Onion",
    t_base=4,  # workbook absolute T min
    t_opt=18.5,  # workbook: midpoint of the supplied optimum band
    t_max=30,  # workbook absolute T max
    t_abs_min=4, t_opt_min=12, t_opt_max=25, t_abs_max=30,  # workbook
    temperature_band_verified=True,
    lue=2.4,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.028,  # TEST VALUE, m²/g
    # Workbook: water band 175-687.5 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=175, water_opt_min_mm=350, water_opt_max_mm=550, water_abs_max_mm=687.5,  # workbook
    water_cycle_days=180,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=100, n_rec_max_kg_ha=150,  # workbook
    p2o5_rec_min_kg_ha=60, p2o5_rec_max_kg_ha=100,  # workbook
    k2o_rec_min_kg_ha=80, k2o_rec_max_kg_ha=150,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.005,  # TEST VALUE
        "stem_tuber": 0.001,  # TEST VALUE
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.15,  # TEST VALUE
        "stem": 0.06,  # TEST VALUE
        "root": 0.05,  # TEST VALUE
        "stem_tuber": 0.5,  # TEST VALUE
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.55,  # TEST VALUE
            "stem": 0.25,  # TEST VALUE
            "root": 0.2,  # TEST VALUE
        },
        "bulbing": {
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.15,  # TEST VALUE
            "root": 0.1,  # TEST VALUE
            "stem_tuber": 0.4,  # TEST VALUE
        },
        "maturation": {
            "leaf": 0.1,  # TEST VALUE
            "stem": 0.05,  # TEST VALUE
            "root": 0.05,  # TEST VALUE
            "stem_tuber": 0.8,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "bulbing": 70,  # TEST VALUE
        "maturation": 131,  # TEST VALUE
    },
    total_biomass_g=60,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 0.5,  # TEST VALUE, g/plant
        "stem": 0.3,  # TEST VALUE, g/plant
        "root": 0.2,  # TEST VALUE, g/plant
    },
    harvestable_organ="stem_tuber",
    cycle_min_days=85, cycle_max_days=175,  # workbook
    first_harvest_min_days=85, first_harvest_max_days=175,  # workbook
)

ONION = CropDefinition(
    parameters=ONION_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"onion": (90, 45, 45)},
    ),
    yield_model=StemTuberYieldModel(),
)
