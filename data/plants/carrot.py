"""Carrot baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import RootTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 20: EcoCrop T 3 / 15-24 / 30 C, cycle 40-150 d, first harvest 60-150 d.
# Workbook harvestable organ: Storage root. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# carrot archetype. The workbook still flags water/nutrient bands as unverified.

CARROT_PARAMETERS = CropParameters(
    name="Carrot",
    t_base=3,  # workbook absolute T min
    t_opt=19.5,  # workbook: midpoint of the supplied optimum band
    t_max=30,  # workbook absolute T max
    t_abs_min=3, t_opt_min=15, t_opt_max=24, t_abs_max=30,  # workbook
    temperature_band_verified=True,
    lue=2.2,  #  
    extinction_k=0.8,  #  
    sla=0.02,  #  , m²/g
    # Air-response profile from Crop_Database: Carrot
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.5,
    vpd_opt_high_kpa=1.1,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.2,
    airflow_opt_high_m_s=0.7,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,

    # Workbook: water band 150-625 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=150, water_opt_min_mm=300, water_opt_max_mm=500, water_abs_max_mm=625,  # workbook
    water_cycle_days=125,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=60, n_rec_max_kg_ha=80,  # workbook
    p2o5_rec_min_kg_ha=40, p2o5_rec_max_kg_ha=60,  # workbook
    k2o_rec_min_kg_ha=40, k2o_rec_max_kg_ha=60,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  #  
        "stem": 0.003,  #  
        "root": 0.006,  #  
        "root_tuber": 0.001,  #  
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.25,  #  
        "stem": 0.15,  #  
        "root": 0.08,  #  
        "root_tuber": 0.8,  #  
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.45,  #  
            "stem": 0.35,  #  
            "root": 0.2,  #  
        },
        "tuber_initiation": {
            "leaf": 0.35,  #  
            "stem": 0.25,  #  
            "root": 0.1,  #  
            "root_tuber": 0.3,  #  
        },
        "bulking": {
            "leaf": 0.12,  #  
            "stem": 0.08,  #  
            "root": 0.05,  #  
            "root_tuber": 0.75,  #  
        },
    },
    phase_start_days={
        "vegetative": 0,  #  
        "tuber_initiation": 27,  #  
        "bulking": 52,  #  
    },
    total_biomass_g=90,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.5,  #  , g/plant
        "stem": 2.0,  #  , g/plant
        "root": 0.2,  #  , g/plant
    },
    harvestable_organ="root_tuber",
    cycle_min_days=40, cycle_max_days=150,  # workbook
    first_harvest_min_days=60, first_harvest_max_days=150,  # workbook
)

CARROT = CropDefinition(
    parameters=CARROT_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"carrot": (90, 45, 45)},
    ),
    yield_model=RootTuberYieldModel(),
)
