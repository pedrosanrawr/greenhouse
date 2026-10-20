import pandas as pd
import streamlit as st

from datetime import date, timedelta
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
st.set_page_config(page_title="Greenhouse Simulator", page_icon="🌱", layout="wide")
WEATHER_START_DATE = date(2001, 1, 1)
WEATHER_END_DATE = date(2025, 12, 31)
DEFAULT_START_DATE = WEATHER_START_DATE
DEFAULT_SIMULATION_DAYS = 120
COVER_TYPE = "Polyethylene film, single layer"
COVER_PAR_TRANSMITTANCE = 0.860

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
    "Custom": {"temperature": 24.0, "airflow": 0.5},
    "Temperate greenhouse": {"temperature": 22.0, "airflow": 0.5},
    "Warm greenhouse": {"temperature": 28.0, "airflow": 0.6},
    "Cool greenhouse": {"temperature": 18.0, "airflow": 0.4},
}
defaults = preset_values[preset_name]

with st.sidebar.expander("Greenhouse conditions", expanded=True):
    temperature = st.number_input("Temperature (°C)", 0.0, 50.0, defaults["temperature"], 0.5)
    airflow = st.slider("Airflow (m/s)", 0.0, 5.0, defaults["airflow"], 0.1)
    water_factor = st.slider("Water availability factor", 0.0, 1.0, 1.0, 0.05)
    nutrient_factor = st.slider("Nutrient availability factor", 0.0, 1.0, 1.0, 0.05)

    simulation_days = st.slider(
        "Simulation duration (days)",
        min_value=30,
        max_value=180,
        value=DEFAULT_SIMULATION_DAYS,
        step=10,
    )

    # Ensure the complete simulation fits within the weather archive.
    latest_start_date = WEATHER_END_DATE - timedelta(
        days=simulation_days - 1
    )

    # Default to the first date in the NASA dataset.
    if "start_date" not in st.session_state:
        st.session_state["start_date"] = DEFAULT_START_DATE

    # Keep the selected date within the permitted range.
    if st.session_state["start_date"] < WEATHER_START_DATE:
        st.session_state["start_date"] = WEATHER_START_DATE

    if st.session_state["start_date"] > latest_start_date:
        st.session_state["start_date"] = latest_start_date

    start_date = st.date_input(
        "Starting date",
        min_value=WEATHER_START_DATE,
        max_value=latest_start_date,
        key="start_date",
    )

    # The entire simulation must fit inside the NASA archive.
    latest_start_date = WEATHER_END_DATE - timedelta(
        days=simulation_days - 1
    )

    # Set a valid initial date and clamp saved selections to the valid range.
    if "simulation_start_date" not in st.session_state:
        st.session_state["simulation_start_date"] = DEFAULT_START_DATE

    if st.session_state["simulation_start_date"] < WEATHER_START_DATE:
        st.session_state["simulation_start_date"] = WEATHER_START_DATE

    if st.session_state["simulation_start_date"] > latest_start_date:
        st.session_state["simulation_start_date"] = latest_start_date

greenhouse = GreenhouseConfig(
    temperature_c=temperature,
    light_hours=16.0,  # Legacy field; not used by the historical light calculation
    irradiance_ppfd=250.0,  # Legacy field; not used by the historical light calculation
    airflow_m_s=airflow,
    water_factor=water_factor,
    nutrient_factor=nutrient_factor,
    start_date=start_date,
    cover_par_transmittance=COVER_PAR_TRANSMITTANCE,
)

st.title("Greenhouse Simulation")
st.caption("Baseline architecture: model contracts, generic model implementations, and a separate simulation engine.")

results = []
for crop_name in selected_crops:
    results.append(run_simulation(CROPS[crop_name], greenhouse, simulation_days, start_date))
all_results = pd.concat(results, ignore_index=True) if results else pd.DataFrame()

overview_tab, charts_tab, details_tab = st.tabs(["Overview", "Charts", "Daily data"])

with overview_tab:
    st.subheader("Simulation setup")
    col1, col2, col3 = st.columns(3)

    col1.metric("Selected crops", len(selected_crops))
    col2.metric("Temperature", f"{temperature:.1f} °C")
    col3.metric("Greenhouse cover", "Single-layer PE")

    st.write(f"**Cover material:** {COVER_TYPE}")
    st.write(
        f"**Cover PAR transmittance:** "
        f"{COVER_PAR_TRANSMITTANCE:.0%}"
    )
    st.write("**Crops:** " + (", ".join(selected_crops) if selected_crops else "None selected"))
    st.write(f"**Greenhouse preset:** {preset_name}")
    st.write(f"**Start date:** {start_date.isoformat()}")
    st.write(f"**Simulation duration:** {simulation_days} days")
    st.write("**Growth model:** Generic biomass growth")
    st.write("**Soil/fertilizer model:** Generic availability-factor fallback")
    st.write("**Yield model:** Generic harvestable-biomass estimate")
    st.warning(
        "This is a structural baseline, not a validated agronomic predictor. "
        "Tomato parameters marked TEST VALUE are provisional. The generic soil model "
        "does not simulate soil pools or fertilizer uptake, and the yield model does "
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
