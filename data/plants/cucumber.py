"""Cucumber baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition
from data.plants.tomato.tomato_yield import TomatoYieldModel

# Workbook ID 5: EcoCrop T 6 / 18-32 / 38 C, cycle 40-180 d, first harvest 40-60 d.
# Workbook harvestable organ: Immature fruit. Harvest mode: Repeated harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# cucumber archetype. The workbook still flags water/nutrient bands as unverified.

CUCUMBER_PARAMETERS = CropParameters(
    name="Cucumber",
    t_base=6,  # workbook absolute T min
    t_opt=25,  # workbook: midpoint of the supplied optimum band
    t_max=38,  # workbook absolute T max
    t_abs_min=6, t_opt_min=18, t_opt_max=32, t_abs_max=38,  # workbook
    temperature_band_verified=True,
    dli_min=20, dli_opt=30,  # workbook
    lue=2.5,  #  
    extinction_k=0.7,  #  
    sla=0.03,  #  , m²/g
    # Air-response profile from Crop_Database: Cucumber
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.32,
    vpd_opt_high_kpa=0.95,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.2,
    airflow_opt_high_m_s=0.7,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,

    # Workbook: water band 200-750 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=200, water_opt_min_mm=400, water_opt_max_mm=600, water_abs_max_mm=750,  # workbook
    water_cycle_days=118,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=100, n_rec_max_kg_ha=140,  # workbook
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=70,  # workbook
    k2o_rec_min_kg_ha=50, k2o_rec_max_kg_ha=70,  # workbook
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
        "flowering": 45,  #  
        "fruiting": 81,  #  
    },
    total_biomass_g=200,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  #  , g/plant
        "stem": 0.5,  #  , g/plant
        "root": 0.3,  #  , g/plant
    },
    harvestable_organ="fruit",
    cycle_min_days=40, cycle_max_days=180,  # workbook
    first_harvest_min_days=40, first_harvest_max_days=60,  # workbook
)

CUCUMBER = CropDefinition(
    parameters=CUCUMBER_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"cucumber": (90, 45, 45)},
    ),
    yield_model=TomatoYieldModel(),
)
