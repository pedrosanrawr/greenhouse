"""Cabbage baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import LeafyYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 27: EcoCrop T 7 / 15-24 / 32 C, cycle 60-200 d, first harvest 60-110 d.
# Workbook harvestable organ: Head. Harvest mode: Single harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# cabbage archetype. The workbook still flags water/nutrient bands as unverified.

CABBAGE_PARAMETERS = CropParameters(
    name="Cabbage",
    t_base=7,  # workbook absolute T min
    t_opt=19.5,  # workbook: midpoint of the supplied optimum band
    t_max=32,  # workbook absolute T max
    t_abs_min=7, t_opt_min=15, t_opt_max=24, t_abs_max=32,  # workbook
    temperature_band_verified=True,
    lue=2.6,  #  
    extinction_k=0.6,  #  
    sla=0.035,  #  , m²/g
    # Air-response profile from Crop_Database: Cabbage
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

    # Workbook: water band 175-625 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=175, water_opt_min_mm=350, water_opt_max_mm=500, water_abs_max_mm=625,  # workbook
    water_cycle_days=130,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=120, n_rec_max_kg_ha=200,  # workbook
    p2o5_rec_min_kg_ha=60, p2o5_rec_max_kg_ha=100,  # workbook
    k2o_rec_min_kg_ha=60, k2o_rec_max_kg_ha=100,  # workbook
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
        "head_fill": 80,  #  
    },
    total_biomass_g=140,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  #  , g/plant
        "stem": 0.3,  #  , g/plant
        "root": 0.2,  #  , g/plant
    },
    harvestable_organ="leaf",
    cycle_min_days=60, cycle_max_days=200,  # workbook
    first_harvest_min_days=60, first_harvest_max_days=110,  # workbook
)

CABBAGE = CropDefinition(
    parameters=CABBAGE_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"cabbage": (90, 45, 45)},
    ),
    yield_model=LeafyYieldModel(),
)
