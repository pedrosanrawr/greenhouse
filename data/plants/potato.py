"""Potato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import StemTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

POTATO_PARAMETERS = CropParameters(
    name="Potato",
    t_base=7.0,
    t_opt=20.0, 
    t_max=30.0,
    t_abs_min=7.0,
    t_opt_min=15.0,
    t_opt_max=25.0,
    t_abs_max=30.0,
    temperature_band_verified=True,
    lue=2.3,   
    extinction_k=0.75,
    sla=0.022,  
    # Air-response profile from Crop_Database: Potato
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


    water_abs_min_mm=250,
    water_opt_min_mm=500,
    water_opt_max_mm=700,
    water_abs_max_mm=875,
    water_cycle_days=125,
    water_band_verified=False,
    n_rec_min_kg_ha=150, n_rec_max_kg_ha=200,  
    p2o5_rec_min_kg_ha=100, p2o5_rec_max_kg_ha=150,  
    k2o_rec_min_kg_ha=100, k2o_rec_max_kg_ha=150,  
    nutrient_rates_verified=False,
    maintenance={
        "leaf": 0.010,  
        "stem": 0.003,  
        "root": 0.006,  
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.001,  
    },

    sink_demand={
        "leaf": 0.12,  
        "stem": 0.06,  
        "root": 0.04,  
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.0,
        "stem_tuber": 0.45,
    },
    biomass_ratio={
        "vegetative": {  # emergence and canopy build-up
            "leaf": 0.50,  
            "stem": 0.30,  
            "root": 0.20,  
        },
        "tuber_initiation": {  # stolon tips start to swell
            "leaf": 0.35,  
            "stem": 0.20,  
            "root": 0.10,  
            "stem_tuber": 0.35,  
        },
        "bulking": {  # tubers fill
            "leaf": 0.15,  
            "stem": 0.07,  
            "root": 0.03,  
            "stem_tuber": 0.75,  
        },
        "maturation": {  # canopy declining, nearly all growth to tubers
            "leaf": 0.05,  
            "stem": 0.03,  
            "root": 0.02,  
            "stem_tuber": 0.90,  
        },
    },
    phase_start_days={
        "vegetative": 0,   
        "tuber_initiation": 25, 
        "bulking": 45,   
        "maturation": 110,   
    },
    total_biomass_g=108.0,   
    initial_biomass={
        "leaf": 0.5,   
        "stem": 0.5,   
        "root": 0.2,   
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
    yield_model=StemTuberYieldModel(),
)