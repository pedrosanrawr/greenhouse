"""Taro baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import StemTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 24: EcoCrop T 10 / 21-28 / 35 C, cycle 180-300 d, first harvest 180-300 d.
# Workbook harvestable organ: Corms/cormels. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# taro archetype. The workbook still flags water/nutrient bands as unverified.

TARO_PARAMETERS = CropParameters(
    name="Taro",
    t_base=10,  # workbook absolute T min
    t_opt=24.5,  # workbook: midpoint of the supplied optimum band
    t_max=35,  # workbook absolute T max
    t_abs_min=10, t_opt_min=21, t_opt_max=28, t_abs_max=35,  # workbook
    temperature_band_verified=True,
    lue=2.4,  #  
    extinction_k=0.7,  #  
    sla=0.028,  #  , m²/g
    # Air-response profile from Crop_Database: Taro
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.4,
    vpd_opt_high_kpa=1.1,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.2,
    airflow_opt_high_m_s=0.7,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,

    # Workbook: water band 250-875 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=250, water_opt_min_mm=500, water_opt_max_mm=700, water_abs_max_mm=875,  # workbook
    water_cycle_days=240,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=100, n_rec_max_kg_ha=150,  # workbook
    p2o5_rec_min_kg_ha=60, p2o5_rec_max_kg_ha=100,  # workbook
    k2o_rec_min_kg_ha=100, k2o_rec_max_kg_ha=150,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  #  
        "stem": 0.003,  #  
        "root": 0.005,  #  
        "stem_tuber": 0.001,  #  
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.15,  #  
        "stem": 0.06,  #  
        "root": 0.05,  #  
        "stem_tuber": 0.5,  #  
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.55,  #  
            "stem": 0.25,  #  
            "root": 0.2,  #  
        },
        "bulbing": {
            "leaf": 0.35,  #  
            "stem": 0.15,  #  
            "root": 0.1,  #  
            "stem_tuber": 0.4,  #  
        },
        "maturation": {
            "leaf": 0.1,  #  
            "stem": 0.05,  #  
            "root": 0.05,  #  
            "stem_tuber": 0.8,  #  
        },
    },
    phase_start_days={
        "vegetative": 0,  #  
        "bulbing": 120,  #  
        "maturation": 225,  #  
    },
    total_biomass_g=260,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 0.5,  #  , g/plant
        "stem": 0.3,  #  , g/plant
        "root": 0.2,  #  , g/plant
    },
    harvestable_organ="stem_tuber",
    cycle_min_days=180, cycle_max_days=300,  # workbook
    first_harvest_min_days=180, first_harvest_max_days=300,  # workbook
)

TARO = CropDefinition(
    parameters=TARO_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"taro": (90, 45, 45)},
    ),
    yield_model=StemTuberYieldModel(),
)
