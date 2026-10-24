"""Sweet potato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import RootTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition


SWEET_POTATO_PARAMETERS = CropParameters(
    name="Sweet potato",
    t_base=10.0,
    t_opt=23.0,   
    t_max=38.0,
    t_abs_min=10.0,
    t_opt_min=18.0,
    t_opt_max=28.0,
    t_abs_max=38.0,
    temperature_band_verified=True,
    lue=2.2,  
    extinction_k=0.8,
    sla=0.02,  
    # Air-response profile from Crop_Database: Sweet potato
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

    water_abs_min_mm=225,
    water_opt_min_mm=450,
    water_opt_max_mm=700,
    water_abs_max_mm=875,
    water_cycle_days=125,
    water_band_verified=False,
    n_rec_min_kg_ha=80, n_rec_max_kg_ha=100,  
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=70,  
    k2o_rec_min_kg_ha=100, k2o_rec_max_kg_ha=140,  
    nutrient_rates_verified=False,
    maintenance={
        "leaf": 0.010,  
        "stem": 0.003,  
        "root": 0.006,  
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.001, 
        "stem_tuber": 0.0,
    },
 
    sink_demand={
        "leaf": 0.25,   
        "stem": 0.15,  
        "root": 0.08,  
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.80, 
        "stem_tuber": 0.0,
    },
    biomass_ratio={
        "vegetative": {  # vine establishment, no storage roots yet
            "leaf": 0.45,   
            "stem": 0.35,   
            "root": 0.20,   
        },
        "tuber_initiation": {  # storage roots begin to form
            "leaf": 0.35,   
            "stem": 0.25,   
            "root": 0.10,   
            "root_tuber": 0.30,   
        },
        "bulking": {  # storage roots dominate
            "leaf": 0.12,   
            "stem": 0.08,   
            "root": 0.05,   
            "root_tuber": 0.75,   
        },
    },
    phase_start_days={
        "vegetative": 0,   
        "tuber_initiation": 30,   
        "bulking": 60,   
    },
    total_biomass_g=310.0,   
    initial_biomass={
        "leaf": 1.5,    
        "stem": 2.0,   
        "root": 0.2,   
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
            recommended_npk={"sweet potato": (90.0, 45.0, 45.0)},
        ),
    yield_model=RootTuberYieldModel(),
)