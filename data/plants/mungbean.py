"""Mungbean baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import SingleHarvestYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 25: EcoCrop T 8 / 21-36 / 40 C, cycle 50-120 d, first harvest 50-120 d.
# Workbook harvestable organ: Dry seeds. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# mungbean archetype. The workbook still flags water/nutrient bands as unverified.
# Harvest mode is single harvest: the whole standing fruit mass is taken on
# the harvest day, so the base SingleHarvestYieldModel is used (it accepts any
# organ). FruitYieldModel would pick the fruit repeatedly, which is wrong here.

MUNGBEAN_PARAMETERS = CropParameters(
    name="Mungbean",
    t_base=8,  # workbook absolute T min
    t_opt=28.5,  # workbook: midpoint of the supplied optimum band
    t_max=40,  # workbook absolute T max
    t_abs_min=8, t_opt_min=21, t_opt_max=36, t_abs_max=40,  # workbook
    temperature_band_verified=True,
    lue=2.5,  #  
    extinction_k=0.7,  #  
    sla=0.03,  #  , m²/g
    # Air-response profile from Crop_Database: Mungbean
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.5,
    vpd_opt_high_kpa=1.2,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.2,
    airflow_opt_high_m_s=0.7,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,

    # Workbook: water band 150-625 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=150, water_opt_min_mm=300, water_opt_max_mm=500, water_abs_max_mm=625,  # workbook
    water_cycle_days=85,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=20, n_rec_max_kg_ha=50,  # workbook
    p2o5_rec_min_kg_ha=30, p2o5_rec_max_kg_ha=60,  # workbook
    k2o_rec_min_kg_ha=30, k2o_rec_max_kg_ha=80,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  #  
        "stem": 0.003,  #  
        "root": 0.006,  #  
        "flower": 0.004,  #  
        "fruit": 0.002,  #  
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.2,  #  
        "stem": 0.1,  #  
        "root": 0.08,  #  
        "flower": 0.02,  #  
        "fruit": 0.25,  #  
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.5,  #  
            "stem": 0.3,  #  
            "root": 0.2,  #  
        },
        "flowering": {
            "leaf": 0.35,  #  
            "stem": 0.3,  #  
            "root": 0.15,  #  
            "flower": 0.1,  #  
            "fruit": 0.1,  #  
        },
        "fruiting": {
            "leaf": 0.2,  #  
            "stem": 0.1,  #  
            "root": 0.08,  #  
            "flower": 0.02,  #  
            "fruit": 0.6,  #  
        },
    },
    phase_start_days={
        "vegetative": 0,  #  
        "flowering": 30,  #  
        "fruiting": 54,  #  
    },
    total_biomass_g=40,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  #  , g/plant
        "stem": 0.5,  #  , g/plant
        "root": 0.3,  #  , g/plant
    },
    harvestable_organ="fruit",
    cycle_min_days=50, cycle_max_days=120,  # workbook
    first_harvest_min_days=50, first_harvest_max_days=120,  # workbook
)

MUNGBEAN = CropDefinition(
    parameters=MUNGBEAN_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"mungbean": (90, 45, 45)},
    ),
    yield_model=SingleHarvestYieldModel(),
)
