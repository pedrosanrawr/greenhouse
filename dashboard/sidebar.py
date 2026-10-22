from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from dashboard.config import (
    COVER_PAR_TRANSMITTANCE,
    COVER_TYPE,
    DEFAULT_SIMULATION_DAYS,
    GREENHOUSE_PRESETS,
    MAX_SELECTED_CROPS,
    MIN_SELECTED_CROPS,
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
        default_crops = crop_names[:MIN_SELECTED_CROPS]
        if "Tomato" in crop_names:
            default_crops = ["Tomato"] + [
                c for c in crop_names if c != "Tomato"
            ][: MIN_SELECTED_CROPS - 1]

        # A session that was started before the cap existed can still hold more
        # than MAX_SELECTED_CROPS entries, which the widget rejects outright.
        # Trim it before the widget is created so the session recovers.
        selection_key = "crop_selection"
        stored = st.session_state.get(selection_key)
        if stored is None:
            st.session_state[selection_key] = default_crops
        elif len(stored) > MAX_SELECTED_CROPS:
            st.session_state[selection_key] = stored[:MAX_SELECTED_CROPS]

        selected_crops = st.multiselect(
            "Crops to simulate",
            options=crop_names,
            key=selection_key,
            max_selections=MAX_SELECTED_CROPS,
            help=(
                f"Select {MIN_SELECTED_CROPS} to {MAX_SELECTED_CROPS} crops. "
                "Selected crops share the same greenhouse and water budget."
            ),
        )

        if len(selected_crops) < MIN_SELECTED_CROPS:
            st.warning(
                f"Select at least {MIN_SELECTED_CROPS} crops "
                f"({len(selected_crops)} selected)."
            )
        else:
            st.caption(f"{len(selected_crops)} crop(s) selected")

        st.divider()

        # ---- 2. Greenhouse conditions ----
        st.subheader("2. Greenhouse conditions")

        preset_name = st.selectbox(
            "",
            list(GREENHOUSE_PRESETS.keys()),
            index=1,
        )
        defaults = GREENHOUSE_PRESETS[preset_name]

        with st.expander("Temperature and air conditions", expanded=True):
            temperature = st.slider(
                "Temperature (°C)",
                min_value=0.0,
                max_value=50.0,
                value=defaults["temperature"],
                step=0.5,
            )

            airflow = st.slider(
                "Air speed at crop canopy (m/s)",
                min_value=0.0,
                max_value=1.5,
                value=defaults["airflow"],
                step=0.05,
                help=(
                    "Use the air speed at or near the plant canopy, "
                    "not the fan outlet speed."
                ),
            )

            relative_humidity_pct = st.slider(
                "Relative humidity (%)",
                min_value=10.0,
                max_value=100.0,
                value=70.0,
                step=1.0,
            )

            st.caption(
                "CO₂ is held fixed at the model reference concentration "
                "of 430 ppm."
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
                    f"Estimated combined daily water requirement: "
                    f"{total_requirement:.1f} L/m²/day. "
                    f"The current budget covers {coverage:.0%}."
                )

                if placeholders:
                    st.caption(
                        f"{placeholders} selected crop(s) use the placeholder "
                        f"requirement of {DEFAULT_WATER_DEMAND_MM_DAY:g} "
                        "L/m²/day because their water bands are not enabled "
                        "as verified model inputs."
                    )

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

            start_date = st.date_input(
                "Starting date",
                value=date.today(),
                help=(
                    "This date sets the simulation calendar. Solar radiation "
                    "uses the multi-year average for each calendar day "
                    "(month and day) across the 2001–2025 dataset, rather "
                    "than the selected year's observed daily value."
                ),
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
        relative_humidity_pct=relative_humidity_pct,
        water_budget_mm_day=water_budget_mm_day,
        fertilizer_n_kg_ha=fertilizer_n,
        fertilizer_p2o5_kg_ha=fertilizer_p2o5,
        fertilizer_k2o_kg_ha=fertilizer_k2o,
        simulation_days=simulation_days,
        start_date=start_date,
    )