# dashboard/sections/kpis.py
import streamlit as st

from dashboard.config import TOTAL_BIOMASS_COLUMNS, YIELD_COLUMNS
from dashboard.utils import (
    first_existing_column,
    format_biomass,
    latest_value,
    safe_number,
)


def render_metric_cards(df, selected_crops, simulation_days):
    total_col = first_existing_column(df, TOTAL_BIOMASS_COLUMNS)
    yield_col = first_existing_column(df, YIELD_COLUMNS)

    final_biomass = 0.0
    biomass_gained = 0.0
    final_harvestable = 0.0

    for crop_name in selected_crops:
        crop_df = df[df["crop"] == crop_name].sort_values("day")
        if crop_df.empty:
            continue

        if total_col:
            final = latest_value(crop_df[total_col])
            first = safe_number(crop_df[total_col].iloc[0])
            final_biomass += final
            biomass_gained += final - first

        if yield_col:
            final_harvestable += latest_value(crop_df[yield_col])

    cols = st.columns(4)

    cols[0].metric(
        "Final biomass",
        format_biomass(final_biomass) if total_col else "N/A",
        help="Sum of the final biomass values for selected crops.",
    )
    cols[1].metric(
        "Biomass gained",
        format_biomass(biomass_gained) if total_col else "N/A",
        help="Final minus first reported biomass, summed across crops.",
    )
    cols[2].metric(
        "Harvestable biomass",
        format_biomass(final_harvestable) if yield_col else "N/A",
        help="Sum of the final values reported by the yield model.",
    )
    cols[3].metric("Simulation period", f"{simulation_days} days")