# dashboard/sections/comparison.py
import pandas as pd
import streamlit as st

from dashboard.charts import line_chart
from dashboard.config import TOTAL_BIOMASS_COLUMNS, YIELD_COLUMNS
from dashboard.utils import first_existing_column, latest_value


def render_comparison(df, selected_crops):
    df = df[df["crop"].isin(selected_crops)]

    total_col = first_existing_column(df, TOTAL_BIOMASS_COLUMNS)
    yield_col = first_existing_column(df, YIELD_COLUMNS)

    if total_col:
        line_chart(
            df,
            total_col,
            "Total biomass (as reported by the model)",
            height=420,
        )

    summary_rows = []
    for crop_name in selected_crops:
        crop_df = df[df["crop"] == crop_name].sort_values("day")
        if crop_df.empty:
            continue

        row = {
            "Crop": crop_name,
            "Days simulated": int(crop_df["day"].nunique()),
        }
        if total_col:
            row["Final biomass"] = latest_value(crop_df[total_col])
        if yield_col:
            row["Final harvestable biomass"] = latest_value(crop_df[yield_col])
        summary_rows.append(row)

    if summary_rows:
        st.markdown("#### Final crop values")
        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Comparisons are most meaningful when crops use compatible units, "
        "starting conditions and model definitions."
    )


def render_data_table(df, selected_crops):
    with st.expander("View daily records and export data", expanded=False):
        data_crop = st.selectbox(
            "Filter by crop",
            options=["All crops"] + list(selected_crops),
            key="daily_data_crop_filter",
        )

        if data_crop == "All crops":
            display_df = df
        else:
            display_df = df[df["crop"] == data_crop]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        st.download_button(
            "Download daily data (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="greenlab_simulation_results.csv",
            mime="text/csv",
        )

        st.caption(
            "The downloaded CSV contains all successfully simulated crops, "
            "regardless of the current table filter."
        )