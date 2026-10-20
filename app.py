import copy

import pandas as pd
import streamlit as st

from datetime import date, timedelta
from data.models.soil import (
    SOIL_TEXTURES,
    DemandLedger,
    IrrigationSchedule,
    NutrientApplication,
    NutrientPools,
    SoilProfile,
    TextureSoilFertilizerModel,
    WaterBalance,
)
from data.models.types import GreenhouseConfig
from data.plants import CROPS
from simulation.engine import run_simulation

ORGAN_COLUMNS = {
    "leaf_biomass_g": "Leaf",
    "stem_biomass_g": "Stem",
    "root_biomass_g": "Root",
    "flower_biomass_g": "Flower",
    "fruit_biomass_g": "Fruit",
    "root_tuber_biomass_g": "Root tuber",
    "stem_tuber_biomass_g": "Stem tuber",
}
NUTRIENT_LABELS = {"n": "N (nitrogen)", "p2o5": "P₂O₅ (phosphorus)", "k2o": "K₂O (potassium)"}
NUTRIENT_DEFAULT_RATES = {"n": 100.0, "p2o5": 60.0, "k2o": 60.0}  # ASSUMPTION: placeholders, kg/ha

st.set_page_config(page_title="Greenhouse Simulator", page_icon="🌱", layout="wide")
WEATHER_START_DATE = date(2001, 1, 1)
WEATHER_END_DATE = date(2025, 12, 31)
DEFAULT_START_DATE = WEATHER_START_DATE
DEFAULT_SIMULATION_DAYS = 120


def build_soil_model(old_model, soil_key, irrigation_mm, interval_days, nutrient_rates):
    """Build a fresh soil model from the sidebar inputs.

    ``nutrient_rates`` maps each selected nutrient ("n", "p2o5", "k2o") to kg/ha.
    Nutrients that are not selected are not modelled and never limit growth.
    The crop's existing demand ledger (recommended rates, etc.) is reused if it has one.
    """
    profile = SoilProfile.build(soil_key)
    irrigation = IrrigationSchedule(interval_days=int(interval_days), amount_mm=float(irrigation_mm))
    application = NutrientApplication(
        nutrient_rates.get("n", 0.0),
        nutrient_rates.get("p2o5", 0.0),
        nutrient_rates.get("k2o", 0.0),
    )
    pools = NutrientPools(application, tracked=tuple(nutrient_rates))
    ledger = getattr(old_model, "demand_ledger", None) or DemandLedger()
    return TextureSoilFertilizerModel.from_components(WaterBalance(profile, irrigation), pools, ledger)


def with_soil_model(crop_definition, soil_model):
    """Copy a crop definition with a different soil model (works even if it is a frozen dataclass)."""
    clone = copy.copy(crop_definition)
    object.__setattr__(clone, "soil_model", soil_model)
    return clone


st.sidebar.title("Greenhouse Simulator")
st.sidebar.subheader("Simulation")

selected_crops = st.sidebar.multiselect(
    "Crop Selection",
    options=list(CROPS.keys()),
    default=["Tomato"],
    help="Only Tomato is configured in this baseline.",
)
if not selected_crops:
    st.sidebar.info("Select Tomato to run the current baseline.")

st.sidebar.subheader("Greenhouse Preset")
preset_name = st.sidebar.selectbox(
    "Preset",
    ["Custom", "Temperate greenhouse", "Warm greenhouse", "Cool greenhouse"],
)
preset_values = {
    "Custom": {"temperature": 24.0, "light_hours": 16.0, "irradiance": 250.0, "airflow": 0.5},
    "Temperate greenhouse": {"temperature": 22.0, "light_hours": 16.0, "irradiance": 250.0, "airflow": 0.5},
    "Warm greenhouse": {"temperature": 28.0, "light_hours": 16.0, "irradiance": 300.0, "airflow": 0.6},
    "Cool greenhouse": {"temperature": 18.0, "light_hours": 14.0, "irradiance": 200.0, "airflow": 0.4},
}
defaults = preset_values[preset_name]

with st.sidebar.expander("Greenhouse conditions", expanded=True):
    temperature = st.number_input("Temperature (°C)", 0.0, 50.0, defaults["temperature"], 0.5)
    light_hours = st.slider("Light period (hours/day)", 0.0, 24.0, defaults["light_hours"], 0.5)
    irradiance = st.number_input(
        "Light irradiance / PPFD (µmol/m²/s)", 0.0, 2500.0, defaults["irradiance"], 10.0
    )
    airflow = st.slider("Airflow (m/s)", 0.0, 5.0, defaults["airflow"], 0.1)
    water_factor = st.slider(
        "Water factor multiplier",
        0.0, 1.0, 1.0, 0.05,
        help="Scales the soil model's daily water factor. 1.0 = no extra restriction.",
    )
    nutrient_factor = st.slider(
        "Nutrient factor multiplier",
        0.0, 1.0, 1.0, 0.05,
        help="Scales the soil model's daily nutrient factor. 1.0 = no extra restriction.",
    )

    simulation_days = st.slider(
        "Simulation duration (days)",
        min_value=30,
        max_value=180,
        value=DEFAULT_SIMULATION_DAYS,
        step=10,
    )

    # The entire simulation must fit inside the NASA archive.
    latest_start_date = WEATHER_END_DATE - timedelta(days=simulation_days - 1)

    # Set a valid initial date and clamp saved selections to the valid range.
    if "simulation_start_date" not in st.session_state:
        st.session_state["simulation_start_date"] = DEFAULT_START_DATE

    if st.session_state["simulation_start_date"] < WEATHER_START_DATE:
        st.session_state["simulation_start_date"] = WEATHER_START_DATE

    if st.session_state["simulation_start_date"] > latest_start_date:
        st.session_state["simulation_start_date"] = latest_start_date

    start_date = st.date_input(
        "Starting date",
        min_value=WEATHER_START_DATE,
        max_value=latest_start_date,
        key="simulation_start_date",
    )

with st.sidebar.expander("Soil, irrigation & fertilizer", expanded=True):
    soil_key = st.selectbox(
        "Soil type",
        options=list(SOIL_TEXTURES),
        index=list(SOIL_TEXTURES).index("loam"),
        format_func=lambda k: SOIL_TEXTURES[k].name,
        help="Hydraulic properties come from Saxton & Rawls (2006) using the preset sand/clay fractions.",
    )
    _h = SoilProfile.build(soil_key).hydraulics
    st.caption(
        f"Wilting point {_h.wilting_point:.3f} · field capacity {_h.field_capacity:.3f} · "
        f"saturation {_h.saturation:.3f} m³/m³ · Ksat {_h.ksat_mm_h:.1f} mm/h"
    )

    irrigation_mm = st.number_input(
        "Irrigation amount (mm per event)", min_value=0.0, max_value=200.0, value=12.0, step=1.0
    )
    irrigation_interval = st.number_input(
        "Irrigation interval (days)", min_value=1, max_value=30, value=3, step=1
    )

    selected_nutrients = st.multiselect(
        "Nutrients to model",
        options=list(NUTRIENT_LABELS),
        default=list(NUTRIENT_LABELS),
        format_func=lambda k: NUTRIENT_LABELS[k],
        help="Selected nutrients are applied on day 0 and can limit growth. "
        "Nutrients not selected are ignored and never limit growth.",
    )
    nutrient_rates = {
        k: st.number_input(
            f"{NUTRIENT_LABELS[k]} applied (kg/ha)",
            min_value=0.0,
            max_value=1000.0,
            value=NUTRIENT_DEFAULT_RATES[k],
            step=5.0,
            key=f"rate_{k}",
        )
        for k in selected_nutrients
    }
    if not selected_nutrients:
        st.info("No nutrients selected: nutrients will not limit growth.")

greenhouse = GreenhouseConfig(
    temperature_c=temperature,
    light_hours=light_hours,
    irradiance_ppfd=irradiance,
    airflow_m_s=airflow,
    water_factor=water_factor,
    nutrient_factor=nutrient_factor,
    start_date=start_date,
)

st.title("Greenhouse Simulation")
st.caption("Baseline architecture: model contracts, generic model implementations, and a separate simulation engine.")

results = []
for crop_name in selected_crops:
    base_crop = CROPS[crop_name]
    soil_model = build_soil_model(
        base_crop.soil_model, soil_key, irrigation_mm, irrigation_interval, nutrient_rates
    )
    results.append(
        run_simulation(with_soil_model(base_crop, soil_model), greenhouse, simulation_days, start_date)
    )
all_results = pd.concat(results, ignore_index=True) if results else pd.DataFrame()

overview_tab, charts_tab, details_tab = st.tabs(["Overview", "Charts", "Daily data"])

with overview_tab:
    st.subheader("Simulation setup")
    col1, col2, col3 = st.columns(3)
    col1.metric("Selected crops", len(selected_crops))
    col2.metric("Temperature", f"{temperature:.1f} °C")
    col3.metric("Light period", f"{light_hours:g} hours/day")
    st.write("**Crops:** " + (", ".join(selected_crops) if selected_crops else "None selected"))
    st.write(f"**Greenhouse preset:** {preset_name}")
    st.write(f"**Start date:** {start_date.isoformat()}")
    st.write(f"**Simulation duration:** {simulation_days} days")
    st.write("**Growth model:** Generic biomass growth")
    st.write(
        f"**Soil/fertilizer model:** TextureSoilFertilizerModel, {SOIL_TEXTURES[soil_key].name}, "
        f"irrigation {irrigation_mm:g} mm every {int(irrigation_interval)} day(s)"
    )
    if nutrient_rates:
        st.write(
            "**Fertilizer applied (day 0):** "
            + ", ".join(f"{NUTRIENT_LABELS[k]} {v:g} kg/ha" for k, v in nutrient_rates.items())
        )
    else:
        st.write("**Fertilizer applied:** none modelled (nutrients do not limit growth)")
    st.write("**Yield model:** Generic harvestable-biomass estimate")
    st.warning(
        "This is a structural baseline, not a validated agronomic predictor. "
        "Tomato parameters marked TEST VALUE are provisional. The texture-based "
        "soil model uses placeholder root-zone depth and demand figures "
        "(marked ASSUMPTION in the code), and crop demand uses fallback "
        "figures rather than the engine's actual uptake. The yield model does "
        "not remove harvested biomass from the plant."
    )

with charts_tab:
    st.subheader("Charts")
    if not all_results.empty:
        st.markdown("**Overall biomass**")
        total_chart = all_results.pivot(index="day", columns="crop", values="total_biomass_g")
        st.line_chart(total_chart, y_label="Total dry biomass (g/plant)", x_label="Day")

        st.markdown("**Biomass by organ**")
        crop_for_organs = st.selectbox("Crop to inspect", selected_crops)
        chart_style = st.radio("Chart style", ["Stacked", "Lines"], horizontal=True)

        organ_rows = all_results[all_results["crop"] == crop_for_organs].set_index("day")
        organ_chart = organ_rows[list(ORGAN_COLUMNS)].rename(columns=ORGAN_COLUMNS)
        organ_chart = organ_chart.loc[:, (organ_chart > 0).any()]

        if chart_style == "Stacked":
            st.area_chart(organ_chart, y_label="Dry biomass (g/plant)", x_label="Day")
        else:
            st.line_chart(organ_chart, y_label="Dry biomass (g/plant)", x_label="Day")

        st.markdown("**Harvestable biomass estimate**")
        yield_chart = all_results.pivot(index="day", columns="crop", values="harvestable_biomass_g")
        st.line_chart(yield_chart, y_label="Estimated harvestable biomass (g/plant)", x_label="Day")

        st.markdown("**Soil water factor**")
        water_chart = all_results.pivot(index="day", columns="crop", values="water_factor")
        st.line_chart(water_chart, y_label="Water factor (0-1)", x_label="Day")

        st.markdown("**Soil nutrient factor**")
        nutrient_chart = all_results.pivot(index="day", columns="crop", values="nutrient_factor")
        st.line_chart(nutrient_chart, y_label="Nutrient factor (0-1)", x_label="Day")
    else:
        st.info("Select Tomato in the sidebar to display simulation charts.")

with details_tab:
    st.subheader("Daily simulation data")
    if not all_results.empty:
        st.dataframe(all_results, use_container_width=True, hide_index=True)
        st.download_button(
            "Download simulation results (CSV)",
            all_results.to_csv(index=False).encode("utf-8"),
            file_name="greenhouse_simulation.csv",
            mime="text/csv",
        )
    else:
        st.info("No simulation results yet.")

st.divider()
st.caption("This is a simplified research prototype. Model contracts can be implemented by crop-specific models later.")