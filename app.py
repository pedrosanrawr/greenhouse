import pandas as pd
import streamlit as st

from data.models.types import GreenhouseConfig
from data.plants import CROPS
from simulation.engine import run_simulation

st.set_page_config(page_title="Greenhouse Simulator", page_icon="🌱", layout="wide")

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
    water_factor = st.slider("Water availability factor", 0.0, 1.0, 1.0, 0.05)
    nutrient_factor = st.slider("Nutrient availability factor", 0.0, 1.0, 1.0, 0.05)
    start_date = st.date_input("Starting date")
    simulation_days = st.slider("Simulation duration (days)", 30, 180, 120, 10)

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
    results.append(run_simulation(CROPS[crop_name], greenhouse, simulation_days, start_date))
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
        organ_rows = all_results[all_results["crop"] == crop_for_organs]
        organ_chart = organ_rows.set_index("day")[
            ["leaf_biomass_g", "stem_biomass_g", "root_biomass_g", "flower_biomass_g", "fruit_biomass_g"]
        ]
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
