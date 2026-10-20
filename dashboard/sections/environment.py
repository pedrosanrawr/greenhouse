# dashboard/sections/environment.py
import streamlit as st

from dashboard.charts import line_chart
from dashboard.config import ENVIRONMENT_COLUMNS
from dashboard.utils import first_existing_column


def render_environment(df):
    available = {}
    for label, names in ENVIRONMENT_COLUMNS.items():
        column = first_existing_column(df, names)
        if column:
            available[label] = column

    if not available:
        st.info(
            "No recognized environmental columns are available "
            "in the simulation output."
        )
        return

    variable = st.selectbox(
        "Environmental variable",
        options=list(available.keys()),
        key="environment_variable_selector",
    )

    line_chart(df, available[variable], variable, height=350)

    if variable in ("Water factor", "Nutrient factor"):
        st.caption(
            "These factors describe the model inputs or outputs. "
            "They should not be interpreted as measured plant stress "
            "unless the model defines and validates them that way."
        )


def render_environment_section(df, settings):
    """Metrics row for the current settings, followed by the variable chart."""
    cols = st.columns(4)
    cols[0].metric("Temperature", f"{settings.temperature:.1f} °C")
    cols[1].metric("Airflow", f"{settings.airflow:.1f} m/s")
    cols[2].metric("Water availability", f"{settings.water_factor:.2f}")
    cols[3].metric("Nutrient availability", f"{settings.nutrient_factor:.2f}")

    render_environment(df)