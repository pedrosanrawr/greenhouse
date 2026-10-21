from datetime import date

# ============================================================
# SIMULATION SETTINGS
# ============================================================

WEATHER_START_DATE = date(2001, 1, 1)
WEATHER_END_DATE = date(2025, 12, 31)
DEFAULT_SIMULATION_DAYS = 120

COVER_TYPE = "Polyethylene film, single layer"
COVER_PAR_TRANSMITTANCE = 0.860

# ============================================================
# OUTPUT COLUMN CANDIDATES
# The first name found in the results dataframe is used.
# ============================================================

TOTAL_BIOMASS_COLUMNS = ["total_biomass_g", "total_living_biomass_g_dm_m2"]
YIELD_COLUMNS = ["harvestable_biomass_g", "cumulative_harvested_yield_g_dm_m2"]
DAILY_PRODUCTION_COLUMNS = [
    "daily_biomass_production_g",
    "daily_biomass_production_g_dm_m2",
    "daily_biomass_increment_g",
]

ORGAN_COLUMNS = {
    "leaf_biomass_g": "Leaf",
    "stem_biomass_g": "Stem",
    "root_biomass_g": "Root",
    "flower_biomass_g": "Flower",
    "fruit_biomass_g": "Fruit",
    "root_tuber_biomass_g": "Root tuber",
    "stem_tuber_biomass_g": "Stem tuber",
    "leaf_biomass_g_dm_m2": "Leaf",
    "stem_biomass_g_dm_m2": "Stem",
    "root_biomass_g_dm_m2": "Root",
    "flower_biomass_g_dm_m2": "Flower",
    "fruit_biomass_g_dm_m2": "Fruit",
    "root_tuber_biomass_g_dm_m2": "Root tuber",
    "stem_tuber_biomass_g_dm_m2": "Stem tuber",
}

# ============================================================
# GREENHOUSE PRESETS
# ============================================================

GREENHOUSE_PRESETS = {
    "Custom":               {"temperature": 24.0, "airflow": 0.5, "water": 1.0, "nutrient": 1.0},
    "Temperate greenhouse": {"temperature": 22.0, "airflow": 0.5, "water": 1.0, "nutrient": 1.0},
    "Warm greenhouse":      {"temperature": 28.0, "airflow": 0.6, "water": 1.0, "nutrient": 1.0},
    "Cool greenhouse":      {"temperature": 18.0, "airflow": 0.4, "water": 1.0, "nutrient": 1.0},
}

# ============================================================
# CHART STYLING
# ============================================================

COLORS = {
    "Leaf": "#8DBB68",
    "Stem": "#C9B45B",
    "Root": "#A97B42",
    "Flower": "#A78BCE",
    "Fruit": "#DF8566",
    "Root tuber": "#C58B56",
    "Stem tuber": "#B2A05B",
}

OLIVE = "#8C9857"

PLOT_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#E8E8E8", "family": "Arial"},
    "margin": {"l": 15, "r": 15, "t": 40, "b": 15},
    "legend": {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
    },
    "hovermode": "x unified",
}

ENVIRONMENT_COLUMNS = {
    "Temperature": ["temperature_c", "temperature"],
    "Daily light integral": ["dli_mol_par_m2_day", "daily_light_integral"],
    "Intercepted PAR": ["intercepted_par_mol_m2_day"],
    "Water factor": ["water_factor", "water_availability_factor"],
    "Nutrient factor": ["nitrogen_factor", "nutrient_factor"],
    "Airflow": ["airflow_m_s"],

    "CO₂ concentration": ["co2_ppm"],
    "Relative humidity": ["relative_humidity_pct"],
    "VPD": ["vpd_kpa"],
    "CO₂ response factor": ["co2_factor"],
    "VPD response factor": ["vpd_factor"],
    "Airflow response factor": ["airflow_factor"],
}

# Score bands: (label, low, high, color)
SCORE_BANDS = [
    ("Poor", 0, 40, "#B5533C"),
    ("Fair", 40, 60, "#C9B45B"),
    ("Good", 60, 80, "#A5B273"),
    ("Optimal", 80, 100, "#8DBB68"),
]

# One fixed color per crop, used in every chart
CROP_PALETTE = [
    "#8DBB68", "#DF8566", "#A78BCE", "#C9B45B",
    "#6FA8C7", "#C58B56", "#D98BB0", "#7FBFA8",
]