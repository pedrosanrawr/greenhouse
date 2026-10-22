"""Kalabasa baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import SingleHarvestYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 11: EcoCrop T 10 / 20-30 / 40 C, cycle 80-140 d, first harvest 80-140 d.
# Workbook harvestable organ: Mature fruit. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL TEST VALUES cloned from the
# kalabasa archetype. The workbook still flags water/nutrient bands as unverified.
# Harvest mode is single harvest: the whole standing fruit mass is taken on
# the harvest day, so the base SingleHarvestYieldModel is used (it accepts any
# organ). FruitYieldModel would pick the fruit repeatedly, which is wrong here.

KALABASA_PARAMETERS = CropParameters(
    name="Kalabasa",
    t_base=10,  # workbook absolute T min
    t_opt=25,  # workbook: midpoint of the supplied optimum band
    t_max=40,  # workbook absolute T max
    t_abs_min=10, t_opt_min=20, t_opt_max=30, t_abs_max=40,  # workbook
    temperature_band_verified=True,
    lue=2.5,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.03,  # TEST VALUE, m²/g
    # Workbook: water band 139.5-593.75 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=139.5, water_opt_min_mm=279, water_opt_max_mm=475, water_abs_max_mm=593.75,  # workbook
    water_cycle_days=108,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=80, n_rec_max_kg_ha=140,  # workbook
    p2o5_rec_min_kg_ha=40, p2o5_rec_max_kg_ha=70,  # workbook
    k2o_rec_min_kg_ha=40, k2o_rec_max_kg_ha=85,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.004,  # TEST VALUE
        "fruit": 0.002,  # TEST VALUE
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.2,  # TEST VALUE
        "stem": 0.1,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.02,  # TEST VALUE
        "fruit": 0.25,  # TEST VALUE
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.5,  # TEST VALUE
            "stem": 0.3,  # TEST VALUE
            "root": 0.2,  # TEST VALUE
        },
        "flowering": {
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.3,  # TEST VALUE
            "root": 0.15,  # TEST VALUE
            "flower": 0.1,  # TEST VALUE
            "fruit": 0.1,  # TEST VALUE
        },
        "fruiting": {
            "leaf": 0.2,  # TEST VALUE
            "stem": 0.1,  # TEST VALUE
            "root": 0.08,  # TEST VALUE
            "flower": 0.02,  # TEST VALUE
            "fruit": 0.6,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "flowering": 35,  # TEST VALUE
        "fruiting": 63,  # TEST VALUE
    },
    total_biomass_g=260,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  # TEST VALUE, g/plant
        "stem": 0.5,  # TEST VALUE, g/plant
        "root": 0.3,  # TEST VALUE, g/plant
    },
    harvestable_organ="fruit",
    cycle_min_days=80, cycle_max_days=140,  # workbook
    first_harvest_min_days=80, first_harvest_max_days=140,  # workbook
)

KALABASA = CropDefinition(
    parameters=KALABASA_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"kalabasa": (90, 45, 45)},
    ),
    yield_model=SingleHarvestYieldModel(),
)
