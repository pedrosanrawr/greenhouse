"""Sweet potato baseline configuration and generic model selections."""
from data.models.generic_growth import GenericCropGrowthModel
from data.models.soil import NutrientApplication, TextureSoilFertilizerModel
from data.models.single_harvest_yield import RootTuberYieldModel
from data.models.types import CropParameters
from data.plants.base import CropDefinition

# Workbook (ID 23, Ipomoea batatas): EcoCrop T 10 / 18-28 / 38 C, cycle 80-170 d,
# first harvest 80-170 d (cycle used as a proxy), reference yield 1.75-2.75 kg/m2
# (typical 2.25) of fresh storage roots, spacing 30 x 90 cm.
# Everything marked TEST VALUE is provisional.
#
# total_biomass_g derivation (TEST VALUE chain):
#   0.30 m x 0.90 m = 0.27 m2/plant -> 2.25 kg/m2 x 0.27 = 0.61 kg fresh roots
#   x ~27% dry matter (TEST) = ~164 g dry roots
#   tuber share of total growth with the ratios below = ~0.54
#   -> ~305 g growth + initial biomass = ~310 g
SWEET_POTATO_PARAMETERS = CropParameters(
    name="Sweet potato",
    t_base=10.0,
    t_opt=23.0,  # TEST VALUE: midpoint of the supplied 18-28 C optimum band
    t_max=38.0,
    t_abs_min=10.0,
    t_opt_min=18.0,
    t_opt_max=28.0,
    t_abs_max=38.0,
    temperature_band_verified=True,
    lue=2.2,  # TEST VALUE
    extinction_k=0.8,  # TEST VALUE
    sla=0.02,  # TEST VALUE, m²/g
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

    # Workbook ID 23: provisional tuber-crop water band 450-700 mm/cycle (the
    # cited study does not confirm it as a verified irrigation-only band).
    # abs_min = 0.5 x 450, opt band = 450-700, abs_max = 1.25 x 700.
    water_abs_min_mm=225,
    water_opt_min_mm=450,
    water_opt_max_mm=700,
    water_abs_max_mm=875,
    water_cycle_days=125,
    water_band_verified=False,
    n_rec_min_kg_ha=80, n_rec_max_kg_ha=100,  # workbook
    p2o5_rec_min_kg_ha=50, p2o5_rec_max_kg_ha=70,  # workbook
    k2o_rec_min_kg_ha=100, k2o_rec_max_kg_ha=140,  # workbook
    nutrient_rates_verified=False,
    maintenance={
        "leaf": 0.010,  # TEST VALUE
        "stem": 0.003,  # TEST VALUE
        "root": 0.006,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.001,  # TEST VALUE
        "stem_tuber": 0.0,
    },
    # Not read by the engine any more; kept because the field is required.
    sink_demand={
        "leaf": 0.25,  # TEST VALUE, g/plant/day
        "stem": 0.15,  # TEST VALUE
        "root": 0.08,  # TEST VALUE
        "flower": 0.0,
        "fruit": 0.0,
        "root_tuber": 0.80,  # TEST VALUE
        "stem_tuber": 0.0,
    },
    biomass_ratio={
        "vegetative": {  # vine establishment, no storage roots yet
            "leaf": 0.45,  # TEST VALUE
            "stem": 0.35,  # TEST VALUE
            "root": 0.20,  # TEST VALUE
        },
        "tuber_initiation": {  # storage roots begin to form
            "leaf": 0.35,  # TEST VALUE
            "stem": 0.25,  # TEST VALUE
            "root": 0.10,  # TEST VALUE
            "root_tuber": 0.30,  # TEST VALUE
        },
        "bulking": {  # storage roots dominate
            "leaf": 0.12,  # TEST VALUE
            "stem": 0.08,  # TEST VALUE
            "root": 0.05,  # TEST VALUE
            "root_tuber": 0.75,  # TEST VALUE
        },
    },
    phase_start_days={
        "vegetative": 0,  # TEST VALUE
        "tuber_initiation": 30,  # TEST VALUE
        "bulking": 60,  # TEST VALUE
    },
    total_biomass_g=310.0,  # TEST VALUE: potential dry mass per plant at cycle end
    initial_biomass={
        "leaf": 1.5,  # TEST VALUE, g/plant (vine cutting)
        "stem": 2.0,  # TEST VALUE
        "root": 0.2,  # TEST VALUE
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