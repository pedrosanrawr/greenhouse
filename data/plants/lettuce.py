"""Lettuce baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import LeafyYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 16: EcoCrop T 5 / 12-21 / 30 C, cycle 35-85 d, first harvest 35-85 d.
# Workbook harvestable organ: Leaves / head. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# lettuce archetype. The workbook still flags water/nutrient bands as unverified.

LETTUCE_PARAMETERS = CropParameters(
    name="Lettuce",
    t_base=5,  # workbook absolute T min
    t_opt=16.5,  # workbook: midpoint of the supplied optimum band
    t_max=30,  # workbook absolute T max
    t_abs_min=5, t_opt_min=12, t_opt_max=21, t_abs_max=30,  # workbook
    temperature_band_verified=True,
    dli_min=12, dli_opt=17,  # workbook
    lue=2.6,  #  
    extinction_k=0.6,  #  
    sla=0.035,  #  , m²/g
    # Air-response profile from Crop_Database: Lettuce
    vpd_low_limit_kpa=0.2,
    vpd_opt_low_kpa=0.63,
    vpd_opt_high_kpa=1.11,
    vpd_high_limit_kpa=2.2,
    vpd_min_factor=0.2,

    airflow_low_limit_m_s=0.05,
    airflow_opt_low_m_s=0.3,
    airflow_opt_high_m_s=0.5,
    airflow_high_limit_m_s=1.2,
    airflow_min_factor=0.2,

    # Workbook: water band 125-500 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=125, water_opt_min_mm=250, water_opt_max_mm=400, water_abs_max_mm=500,  # workbook
    water_cycle_days=60,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=40, n_rec_max_kg_ha=70,  # workbook
    p2o5_rec_min_kg_ha=30, p2o5_rec_max_kg_ha=50,  # workbook
    k2o_rec_min_kg_ha=30, k2o_rec_max_kg_ha=50,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.012,  #  
        "stem": 0.004,  #  
        "root": 0.006,  #  
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.35,  #  
        "stem": 0.1,  #  
        "root": 0.06,  #  
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.65,  #  
            "stem": 0.2,  #  
            "root": 0.15,  #  
        },
        "head_fill": {
            "leaf": 0.8,  #  
            "stem": 0.12,  #  
            "root": 0.08,  #  
        },
    },
    phase_start_days={
        "vegetative": 0,  #  
        "head_fill": 34,  #  
    },
    total_biomass_g=45,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  #  , g/plant
        "stem": 0.3,  #  , g/plant
        "root": 0.2,  #  , g/plant
    },
    harvestable_organ="leaf",
    cycle_min_days=35, cycle_max_days=85,  # workbook
    first_harvest_min_days=35, first_harvest_max_days=85,  # workbook
)

LETTUCE = CropDefinition(
    parameters=LETTUCE_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"lettuce": (90, 45, 45)},
    ),
    yield_model=LeafyYieldModel(),
)
