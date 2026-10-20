# dashboard/sections/biomass.py
import streamlit as st

from dashboard.charts import line_chart
from dashboard.config import (
    DAILY_PRODUCTION_COLUMNS,
    TOTAL_BIOMASS_COLUMNS,
    YIELD_COLUMNS,
)
from dashboard.utils import first_existing_column


def render_total_biomass(df):
    col = first_existing_column(df, TOTAL_BIOMASS_COLUMNS)
    if not col:
        st.info("Total biomass is not available in the simulation output.")
        return

    line_chart(
        df,
        col,
        "Total biomass (as reported by the model)",
        height=410,
    )


def render_daily_production(df):
    col = first_existing_column(df, DAILY_PRODUCTION_COLUMNS)
    if not col:
        st.info(
            "Daily biomass production is not available as a separate "
            "output column yet."
        )
        return

    line_chart(
        df,
        col,
        "Daily biomass production (model units/day)",
    )


def render_harvest(df):
    col = first_existing_column(df, YIELD_COLUMNS)
    if not col:
        st.info(
            "No recognized harvestable-biomass or cumulative-harvest "
            "column was found."
        )
        return

    line_chart(
        df,
        col,
        "Harvestable biomass (model units)",
    )