"""Tomato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition
from data.plants.tomato.tomato_yield import TomatoYieldModel

# Temperature boundaries and broad timing ranges are based on the supplied
TOMATO_PARAMETERS = CropParameters(
    name="Tomato",
    t_base=7.0,
    t_opt=23.5,  # midpoint of the supplied 20–27 C optimum band
    t_max=35.0,
    t_abs_min=7.0,
    t_opt_min=20.0,
    t_opt_max=27.0,
    t_abs_max=35.0,
    temperature_band_verified=True,
    dli_min=20,
    dli_opt=30,
    lue=2.5,
    extinction_k=0.7,  
    sla=0.03,  
    # Air-response profile from Crop_Database: Tomato
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.95,
    vpd_opt_high_kpa=1.58,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.5,
    airflow_opt_high_m_s=1.0,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,
    
    water_abs_min_mm=200,
    water_opt_min_mm=400,
    water_opt_max_mm=800,
    water_abs_max_mm=1000,
    water_cycle_days=158,  
    water_band_verified=False,
    n_rec_min_kg_ha=100, n_rec_max_kg_ha=180,  
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=90,
    k2o_rec_min_kg_ha=50, k2o_rec_max_kg_ha=90,  
    nutrient_rates_verified=False,
    maintenance={
        "leaf": 0.010,    
        "stem": 0.003,    
        "root": 0.006,    
        "flower": 0.004,    
        "fruit": 0.002,    
    },
    sink_demand={
        "leaf": 0.20,  
        "stem": 0.10,    
        "root": 0.08,    
        "flower": 0.02,    
        "fruit": 0.25,    
    },
    
    biomass_ratio={
        "vegetative": {
            "leaf": 0.50,    
            "stem": 0.30,    
            "root": 0.20,    
        },
        "flowering": {
            "leaf": 0.35,    
            "stem": 0.30,    
            "root": 0.15,    
            "flower": 0.10,    
            "fruit": 0.10,  
        },
        "fruiting": {
            "leaf": 0.20,   
            "stem": 0.10,    
            "root": 0.08,    
            "flower": 0.02,    
            "fruit": 0.60,   
        },
    },
    initial_biomass={
        "leaf": 1.0,  
        "stem": 0.5,    
        "root": 0.3,    
        "flower": 0.0,
        "fruit": 0.0,  
    },
    harvestable_organ="fruit",
    cycle_min_days=70,
    cycle_max_days=150,
    first_harvest_min_days=70,
    first_harvest_max_days=130,
        # Day each phase starts. Fruiting begins before first_harvest_min_days (70).
    phase_start_days={
        "vegetative": 0,   #  
        "flowering": 35,   #  
        "fruiting": 65,    #  
    },
    total_biomass_g=150.0,  #  : potential dry mass per plant at cycle end
)

TOMATO = CropDefinition(
    parameters=TOMATO_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"tomato": (90.0, 45.0, 45.0)},
    ),
    yield_model=TomatoYieldModel(),
)