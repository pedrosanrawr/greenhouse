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

    if "response factor" in variable.lower():
        st.caption(
            "A factor of 1.0 can mean the response is inactive because "
            "crop-specific parameters have not been configured. Check "
            "the active-response fields in the simulation data."
        )


def render_environment_section(df, settings):
    """Metrics row for the current settings, followed by the variable chart."""
    cols = st.columns(6)

    cols[0].metric("Temperature", f"{settings.temperature:.1f} °C")
    cols[1].metric("Airflow", f"{settings.airflow:.2f} m/s")
    cols[2].metric("CO₂", f"{settings.co2_ppm:.0f} ppm")
    cols[3].metric(
        "Relative humidity",
        f"{settings.relative_humidity_pct:.0f}%",
    )
    cols[4].metric("Water availability", f"{settings.water_factor:.2f}")
    cols[5].metric("Nutrient availability", f"{settings.nutrient_factor:.2f}")

    render_environment(df)
