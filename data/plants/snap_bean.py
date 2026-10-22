"""Snap bean baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition
from data.plants.tomato.tomato_yield import TomatoYieldModel

# Workbook ID 26: EcoCrop T 7 / 16-25 / 32 C, cycle 50-270 d, first harvest 50-70 d.
# Workbook harvestable organ: Green pods. Harvest mode: Repeated harvest.
# Temperature band, cycle, first-harvest, water and nutrient bands are from the
# supplied crop workbook. Model coefficients, biomass ratios and total_biomass_g
# are NOT in the workbook; they are PROVISIONAL TEST VALUES cloned from the
# snap_bean archetype. The workbook still flags water/nutrient bands as unverified.

SNAP_BEAN_PARAMETERS = CropParameters(
    name="Snap bean",
    t_base=7,  # workbook absolute T min
    t_opt=20.5,  # workbook: midpoint of the supplied optimum band
    t_max=32,  # workbook absolute T max
    t_abs_min=7, t_opt_min=16, t_opt_max=25, t_abs_max=32,  # workbook
    temperature_band_verified=True,
    lue=2.5,  # TEST VALUE
    extinction_k=0.7,  # TEST VALUE
    sla=0.03,  # TEST VALUE, m²/g
    # Workbook: water band 150-625 mm/cycle (abs_min = 0.5 x opt_min, abs_max = 1.25 x opt_max).
    water_abs_min_mm=150, water_opt_min_mm=300, water_opt_max_mm=500, water_abs_max_mm=625,  # workbook
    water_cycle_days=83,  # workbook
    water_band_verified=False,  # workbook flags this band unverified
    n_rec_min_kg_ha=30, n_rec_max_kg_ha=50,  # workbook
    p2o5_rec_min_kg_ha=60, p2o5_rec_max_kg_ha=100,  # workbook
    k2o_rec_min_kg_ha=30, k2o_rec_max_kg_ha=80,  # workbook
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
        "flowering": 67,  # TEST VALUE
        "fruiting": 121,  # TEST VALUE
    },
    total_biomass_g=80,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.0,  # TEST VALUE, g/plant
        "stem": 0.5,  # TEST VALUE, g/plant
        "root": 0.3,  # TEST VALUE, g/plant
    },
    harvestable_organ="fruit",
    cycle_min_days=50, cycle_max_days=270,  # workbook
    first_harvest_min_days=50, first_harvest_max_days=70,  # workbook
)

SNAP_BEAN = CropDefinition(
    parameters=SNAP_BEAN_PARAMETERS,
    growth_model=GenericCropGrowthModel(),
    soil_model=TextureSoilFertilizerModel(
        "clay_loam",
        nutrients=NutrientApplication(100, 60, 60),
        recommended_npk={"snap bean": (90, 45, 45)},
    ),
    yield_model=TomatoYieldModel(),
)
