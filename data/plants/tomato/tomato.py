"""Tomato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.generic_yield import GenericYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition
from data.plants.tomato.tomato_yield import TomatoYieldModel

# Temperature boundaries and broad timing ranges are based on the supplied
# greenhouse crop spreadsheet. The 24 C optimum is a TEST VALUE midpoint.
# Remaining coefficients and biomass values are provisional TEST VALUES.
TOMATO_PARAMETERS = CropParameters(
    name="Tomato",
    t_base=7.0,
    t_opt=24.0,  # TEST VALUE: midpoint of the supplied 20–27 C optimum band
    t_max=35.0,
    t_abs_min=7.0,
    t_opt_min=20.0,
    t_opt_max=27.0,
    t_abs_max=35.0,
    temperature_band_verified=True,
    dli_min=20,
    dli_opt=30,
    lue=2.5,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.03,  # TEST VALUE, m²/g
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
    
    water_abs_min_mm=300,   # DUMMY test value, not sourced
    water_opt_min_mm=400,   # DUMMY
    water_opt_max_mm=600,   # DUMMY
    water_abs_max_mm=900,   # DUMMY
    water_cycle_days=100,   # DUMMY
    water_band_verified=True,
    n_rec_min_kg_ha=100, n_rec_max_kg_ha=150, n_excess_kg_ha=300,        # DUMMY
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=80,                        # DUMMY
    k2o_rec_min_kg_ha=60, k2o_rec_max_kg_ha=100,                         # DUMMY
    nutrient_rates_verified=True,
    maintenance={
        "leaf": 0.010,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.004,  # TEST VALUE
        "fruit": 0.002,  # TEST VALUE
    },
    sink_demand={
        "leaf": 0.20,  # TEST VALUE, g/plant/day
        "stem": 0.10,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.02,  # TEST VALUE
        "fruit": 0.25,  # TEST VALUE
    },
    # Fraction of new biomass allocated to each organ, per phase.
    # Each phase sums to 1.0. Omitted organs (root_tuber, stem_tuber) are
    # auto-filled with 0. Keep phases in development order.
    biomass_ratio={
        "vegetative": {
            "leaf": 0.50,  # TEST VALUE
            "stem": 0.30,  # TEST VALUE
            "root": 0.20,  # TEST VALUE
        },
        "flowering": {
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.30,  # TEST VALUE
            "root": 0.15,  # TEST VALUE
            "flower": 0.10,  # TEST VALUE
            "fruit": 0.10,  # TEST VALUE
        },
        "fruiting": {
            "leaf": 0.20,  # TEST VALUE
            "stem": 0.10,  # TEST VALUE
            "root": 0.08,  # TEST VALUE
            "flower": 0.02,  # TEST VALUE
            "fruit": 0.60,  # TEST VALUE
        },
    },
    initial_biomass={
        "leaf": 1.0,  # TEST VALUE, g/plant
        "stem": 0.5,  # TEST VALUE
        "root": 0.3,  # TEST VALUE
        "flower": 0.0,  # TEST VALUE
        "fruit": 0.0,  # TEST VALUE
    },
    harvestable_organ="fruit",
    cycle_min_days=70,
    cycle_max_days=150,
    first_harvest_min_days=70,
    first_harvest_max_days=130,
        # Day each phase starts. Fruiting begins before first_harvest_min_days (70).
    phase_start_days={
        "vegetative": 0,   # TEST VALUE
        "flowering": 35,   # TEST VALUE
        "fruiting": 65,    # TEST VALUE
    },
    total_biomass_g=150.0,  # TEST VALUE: potential dry mass per plant at cycle end
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