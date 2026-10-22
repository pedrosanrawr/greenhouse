"""Patola baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition
from data.plants.tomato.tomato_yield import TomatoYieldModel

# Workbook ID 10: EcoCrop T 15 / 20-32 / 38 C, cycle 40-150 d, first harvest 40-70 d.
# Workbook harvestable organ: Immature fruit. Harvest mode: Repeated harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL TEST VALUES cloned from the
# patola archetype. The workbook still flags water/nutrient bands as unverified.

PATOLA_PARAMETERS = CropParameters(
    name="Patola",
    t_base=15,  # workbook absolute T min
    t_opt=26,  # workbook: midpoint of the supplied optimum band
    t_max=38,  # workbook absolute T max
    t_abs_min=15, t_opt_min=20, t_opt_max=32, t_abs_max=38,  # workbook
    temperature_band_verified=True,
    lue=2.5,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.03,  # TEST VALUE, m²/g
    # Air-response profile from Crop_Database: Patola
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
    water_cycle_days=95,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=80, n_rec_max_kg_ha=140,  # workbook
    p2o5_rec_min_kg_ha=40, p2o5_rec_max_kg_ha=70,  # workbook
    k2o_rec_min_kg_ha=40, k2o_rec_max_kg_ha=70,  # workbook
    nutrient_rates_verified=False,  # workbook flags these rates unverified
    maintenance={
        "leaf": 0.01,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.004,  # TEST VALUE
        "fruit": 0.002,  # TEST VALUE
    },
    # Organ sink-demand coefficients read by the growth model each day.
    sink_demand={
        "leaf": 0.2,  # TEST VALUE
        "stem": 0.1,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.02,  # TEST VALUE
        "fruit": 0.25,  # TEST VALUE
    },
    biomass_ratio={
        "vegetative": {
            "leaf": 0.5,  # TEST VALUE
            "stem": 0.3,  # TEST VALUE
            "root": 0.2,  # TEST VALUE
        },
        "flowering": {
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.3,  # TEST VALUE
            "root": 0.15,  # TEST VALUE
            "flower": 0.1,  # TEST VALUE
            "fruit": 0.1,  # TEST VALUE
        },
        "fruiting": {
            "leaf": 0.2,  # TEST VALUE
            "stem": 0.1,  # TEST VALUE
            "root": 0.08,  # TEST VALUE
            "flower": 0.02,  # TEST VALUE
            "fruit": 0.6,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "flowering": 37,  # TEST VALUE
        "fruiting": 67,  # TEST VALUE
    },
    total_biomass_g=200,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  # TEST VALUE, g/plant
        "stem": 0.5,  # TEST VALUE, g/plant
        "root": 0.3,  # TEST VALUE, g/plant
    },
    harvestable_organ="fruit",
    cycle_min_days=40, cycle_max_days=150,  # workbook
    first_harvest_min_days=40, first_harvest_max_days=70,  # workbook
)

PATOLA = CropDefinition(
    parameters=PATOLA_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"patola": (90, 45, 45)},
    ),
    yield_model=TomatoYieldModel(),
)
