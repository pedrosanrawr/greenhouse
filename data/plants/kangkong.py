"""Kangkong baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import LeafyYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook ID 14: EcoCrop T 10 / 15-35 / 40 C, cycle 30-70 d, first harvest 30-70 d.
# Workbook harvestable organ: Young shoots and leaves. Harvest mode: Repeated harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL  S cloned from the
# kangkong archetype. The workbook still flags water/nutrient bands as unverified.
# Harvest mode is repeated harvest, but the shared models have no repeated-cut
# mechanism for leaves: LeafyYieldModel takes the standing leaf mass once, at
# the end of the season. The total is the season's leaf production; the number
# of cuts is not modelled.

KANGKONG_PARAMETERS = CropParameters(
    name="Kangkong",
    t_base=10,  # workbook absolute T min
    t_opt=25,  # workbook: midpoint of the supplied optimum band
    t_max=40,  # workbook absolute T max
    t_abs_min=10, t_opt_min=15, t_opt_max=35, t_abs_max=40,  # workbook
    temperature_band_verified=True,
    lue=2.6,  #  
    extinction_k=0.6,  #  
    sla=0.035,  #  , m²/g
    # Air-response profile from Crop_Database: Kangkong
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

    # Workbook: water band 150-562.5 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=150, water_opt_min_mm=300, water_opt_max_mm=450, water_abs_max_mm=562.5,  # workbook
    water_cycle_days=50,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=40, n_rec_max_kg_ha=80,  # workbook
    p2o5_rec_min_kg_ha=30, p2o5_rec_max_kg_ha=60,  # workbook
    k2o_rec_min_kg_ha=30, k2o_rec_max_kg_ha=60,  # workbook
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
        "regrowth": {
            "leaf": 0.78,  #  
            "stem": 0.14,  #  
            "root": 0.08,  #  
        },
    },
    phase_start_days={
        "vegetative": 0,  #  
        "regrowth": 17,  #  
    },
    total_biomass_g=60,  #  : potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  #  , g/plant
        "stem": 0.3,  #  , g/plant
        "root": 0.2,  #  , g/plant
    },
    harvestable_organ="leaf",
    cycle_min_days=30, cycle_max_days=70,  # workbook
    first_harvest_min_days=30, first_harvest_max_days=70,  # workbook
)

KANGKONG = CropDefinition(
    parameters=KANGKONG_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"kangkong": (90, 45, 45)},
    ),
    yield_model=LeafyYieldModel(),
)
