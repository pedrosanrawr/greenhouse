from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from dashboard.config import (
    COVER_PAR_TRANSMITTANCE,
    COVER_TYPE,
    DEFAULT_SIMULATION_DAYS,
    GREENHOUSE_PRESETS,
    WEATHER_END_DATE,
    WEATHER_START_DATE,
)
from data.models.water_budget import (
    DEFAULT_WATER_DEMAND_MM_DAY,
    water_requirement_mm_day,
)
from data.plants import CROPS

# Placeholder fertilizer rates (kg/ha), the same baseline the soil model uses.
DEFAULT_FERTILIZER_N_KG_HA = 100.0
DEFAULT_FERTILIZER_P2O5_KG_HA = 60.0
DEFAULT_FERTILIZER_K2O_KG_HA = 60.0


@dataclass
class SidebarSettings:
    selected_crops: list
    preset_name: str
    temperature: float
    airflow: float
    co2_ppm: float
    relative_humidity_pct: float
    water_budget_mm_day: float
    fertilizer_n_kg_ha: float
    fertilizer_p2o5_kg_ha: float
    fertilizer_k2o_kg_ha: float
    simulation_days: int
    start_date: date

    @property
    def fertilizer_npk(self):
        return (
            self.fertilizer_n_kg_ha,
            self.fertilizer_p2o5_kg_ha,
            self.fertilizer_k2o_kg_ha,
        )


def _combined_water_requirement(selected_crops):
    """Sum of the selected crops' daily water requirements, in L/m^2.

    Crops without a verified water band use the 4 L/m^2 placeholder.
    Returns (total, number of crops using the placeholder).
    """
    total, placeholders = 0.0, 0
    for name in selected_crops:
        requirement = water_requirement_mm_day(CROPS[name].parameters)
        if requirement is None:
            requirement = DEFAULT_WATER_DEMAND_MM_DAY
            placeholders += 1
        total += requirement
    return total, placeholders


def render_sidebar() -> SidebarSettings:
    with st.sidebar:
        with st.container(horizontal=True, vertical_alignment="center", gap=10):
            st.image("assets/logo.svg", width=44)
            st.markdown("# GREENLAB")
        st.caption("Greenhouse simulation workspace")
        st.divider()

        # ---- 1. Crop selection ----
        st.subheader("1. Crop selection")

        crop_names = list(CROPS.keys())
        default_crops = ["Tomato"] if "Tomato" in crop_names else crop_names[:1]

        selected_crops = st.multiselect(
            "Crops to simulate",
            options=crop_names,
            default=default_crops,
            help="Selected crops share the same greenhouse and water budget.",
        )

        if selected_crops:
            st.caption(f"{len(selected_crops)} crop(s) selected")
        else:
            st.warning("Select at least one crop.")

        st.divider()

        # ---- 2. Greenhouse conditions ----
        st.subheader("2. Greenhouse conditions")

        preset_name = st.selectbox(
            "",
            list(GREENHOUSE_PRESETS.keys()),
            index=1,
        )
        defaults = GREENHOUSE_PRESETS[preset_name]

        with st.expander("Temperature and airflow", expanded=True):
            temperature = st.slider(
                "Temperature (°C)",
                min_value=0.0,
                max_value=50.0,
                value=defaults["temperature"],
                step=0.5,
            )
            airflow = st.slider(
                "Airflow (m/s)",
                min_value=0.0,
                max_value=5.0,
                value=defaults["airflow"],
                step=0.1,
            )
            co2_ppm = st.number_input(
                "CO₂ (ppm)",
                min_value=200.0,
                max_value=2000.0,
                value=426.0,
                step=10.0,
            )
            relative_humidity_pct = st.slider(
                "Relative humidity (%)",
                min_value=10.0,
                max_value=100.0,
                value=70.0,
                step=1.0,
            )

        with st.expander("Water and fertilizer", expanded=True):
            total_requirement, placeholders = _combined_water_requirement(
                selected_crops
            )
            suggested = round(total_requirement, 1) if selected_crops else (
                DEFAULT_WATER_DEMAND_MM_DAY
            )

            # The key includes the selection, so the suggested budget resets
            # whenever the set of crops changes.
            water_budget_mm_day = st.number_input(
                "Water budget (L/m^2, shared by all crops)",
                min_value=0.0,
                max_value=200.0,
                value=float(suggested),
                step=0.5,
                key="water_budget_" + "|".join(selected_crops),
                help=(
                    "Total daily water for the whole greenhouse. "
                    "It is split between the selected crops in "
                    "proportion to each crop's daily water requirement."
                ),
            )

            if selected_crops and total_requirement > 0:
                coverage = water_budget_mm_day / total_requirement
                st.caption(
                    f"The selected crops need about {total_requirement:.1f} "
                    f"1L/m^2 combined. This budget covers {coverage:.0%} of that."
                )
                # if placeholders:
                #     st.caption(
                #         f"{placeholders} crop(s) have no verified water "
                #         f"requirement and use a placeholder of "
                #         f"{DEFAULT_WATER_DEMAND_MM_DAY:g} L/m^2."
                #     )

            st.markdown("**Fertilizer applied at the start (kg/ha)**")
            fertilizer_n = st.number_input(
                "Nitrogen (N)",
                min_value=0.0,
                max_value=1000.0,
                value=DEFAULT_FERTILIZER_N_KG_HA,
                step=5.0,
                help="kg N per hectare, applied on day 0 to each crop.",
            )
            fertilizer_p2o5 = st.number_input(
                "Phosphate (P₂O₅)",
                min_value=0.0,
                max_value=1000.0,
                value=DEFAULT_FERTILIZER_P2O5_KG_HA,
                step=5.0,
                help="kg P₂O₅ per hectare, applied on day 0 to each crop.",
            )
            fertilizer_k2o = st.number_input(
                "Potash (K₂O)",
                min_value=0.0,
                max_value=1000.0,
                value=DEFAULT_FERTILIZER_K2O_KG_HA,
                step=5.0,
                help="kg K₂O per hectare, applied on day 0 to each crop.",
            )

        with st.expander("Simulation period", expanded=True):
            simulation_days = st.select_slider(
                "Duration",
                options=list(range(30, 181, 10)),
                value=DEFAULT_SIMULATION_DAYS,
                format_func=lambda value: f"{value} days",
            )

            latest_start_date = WEATHER_END_DATE - timedelta(days=simulation_days - 1)

            start_date = st.date_input(
                "Starting date",
                value=WEATHER_START_DATE,
                min_value=WEATHER_START_DATE,
                max_value=latest_start_date,
                help="The selected simulation period must fit in the configured archive.",
            )

        # with st.expander("Advanced assumptions", expanded=False):
        #     st.text_input(
        #         "Greenhouse cover",
        #         value=COVER_TYPE,
        #         disabled=True,
        #     )
        #     st.number_input(
        #         "Cover PAR transmittance",
        #         min_value=0.0,
        #         max_value=1.0,
        #         value=COVER_PAR_TRANSMITTANCE,
        #         disabled=True,
        #     )
        #     st.caption(
        #         "Water availability and nutrient availability are calculated "
        #         "by the soil model from the water budget and fertilizer "
        #         "above. They are no longer set by hand."
        #     )

        st.divider()
        st.caption("Results update automatically when settings change.")

    return SidebarSettings(
        selected_crops=selected_crops,
        preset_name=preset_name,
        temperature=temperature,
        airflow=airflow,
        co2_ppm=co2_ppm,
        relative_humidity_pct=relative_humidity_pct,
        water_budget_mm_day=water_budget_mm_day,
        fertilizer_n_kg_ha=fertilizer_n,
        fertilizer_p2o5_kg_ha=fertilizer_p2o5,
        fertilizer_k2o_kg_ha=fertilizer_k2o,
        simulation_days=simulation_days,
        start_date=start_date,
    )