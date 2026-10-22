# dashboard/sections/details.py
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from dashboard.charts import plot_layout
from dashboard.config import (
    DAILY_PRODUCTION_COLUMNS,
    TOTAL_BIOMASS_COLUMNS,
    YIELD_COLUMNS,
)
from dashboard.sections.biomass import (
    render_daily_production,
    render_harvest,
    render_total_biomass,
)
from dashboard.sections.common import CHART_CONFIG, how_to_read
from dashboard.sections.comparison import render_data_table
from dashboard.sections.environment import render_environment_section
from dashboard.utils import first_existing_column

MODELED_FACTOR_COLUMNS = {
    "Temperature": "temperature_factor",
    "Water availability": "water_factor",
    "Nutrient availability": "nutrient_factor",
    "VPD": "vpd_factor",
    "Canopy air speed": "airflow_factor",
}


def _modeled_factor_data(df):
    factor_columns = [
        column
        for column in MODELED_FACTOR_COLUMNS.values()
        if column in df.columns
    ]

    if not factor_columns or not {"crop", "day"}.issubset(df.columns):
        return pd.DataFrame(), factor_columns

    data = df[["crop", "day", *factor_columns]].copy().reset_index(drop=True)

    for column in factor_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["_lowest_factor"] = data[factor_columns].min(axis=1, skipna=True)
    data = data.dropna(subset=["_lowest_factor"])

    return data, factor_columns

def _interpretation(text):
    with st.container(border=True):
        st.markdown("**Interpretation of data**")
        st.write(text)


def _render_measure_interpretation(df, column_candidates, label, mode):
    column = first_existing_column(df, column_candidates)
    if not column or df.empty:
        _interpretation(f"{label} is not available in the simulation output.")
        return

    values = pd.to_numeric(df[column], errors="coerce")
    valid = df.loc[values.notna()].copy()
    valid[column] = values.loc[values.notna()]
    valid = valid.reset_index(drop=True)
    if valid.empty:
        _interpretation(f"{label} has no numeric values to interpret.")
        return

    if mode == "production":
        average = valid[column].mean()
        peak_index = valid[column].idxmax()
        peak = valid.loc[peak_index]
        crop = peak.get("crop", "the selected crop")
        day = pd.to_numeric(peak.get("day"), errors="coerce")
        day_text = f" on day {day:g}" if pd.notna(day) else ""
        _interpretation(
            f"Average granted growth was {average:.2f} g dry mass per plant "
            f"per day across the selected crop-days. "
            f"The highest recorded value was {peak[column]:.2f} for {crop}"
            f"{day_text}."
        )
        return

    if mode == "environment":
        _interpretation(
            f"{label} averaged {valid[column].mean():.2f} across the run, "
            f"with values from {valid[column].min():.2f} to "
            f"{valid[column].max():.2f}. Interpret this range using the "
            "selected variable's units and model definition."
        )
        return

    summaries = []
    groups = valid.groupby("crop", sort=False) if "crop" in valid else [(label, valid)]
    for crop, crop_df in groups:
        if "day" in crop_df:
            crop_df = crop_df.sort_values("day")
        start, end = crop_df[column].iloc[0], crop_df[column].iloc[-1]
        change = end - start
        direction = "increased" if change > 0 else "decreased" if change < 0 else "stayed level"
        summaries.append(f"{crop} {direction} from {start:.2f} to {end:.2f}")
    _interpretation(f"{label}: " + "; ".join(summaries) + ".")


def _render_stress_interpretation(df):
    data, factor_columns = _modeled_factor_data(df)

    if data.empty:
        _interpretation(
            "No modeled limitation-factor data is available to interpret."
        )
        return

    mean_value = data["_lowest_factor"].mean()

    if mean_value >= 1.0 and data["_lowest_factor"].min() >= 1.0:
        _interpretation(
            "None of the included response or availability factors fell "
            "below 1.00 during this run. This is a model diagnostic, not "
            "a validated measure of total plant stress."
        )
        return

    worst = data.loc[data["_lowest_factor"].idxmin()]
    factor_column = worst[factor_columns].idxmin()
    factor_label = next(
        label
        for label, column in MODELED_FACTOR_COLUMNS.items()
        if column == factor_column
    )

    day = pd.to_numeric(worst["day"], errors="coerce")
    day_text = f" on day {day:g}" if pd.notna(day) else ""

    _interpretation(
        f"The lowest modeled factor averaged {mean_value:.2f} across "
        f"the selected crop-days. The lowest value was "
        f"{worst['_lowest_factor']:.2f} for {worst['crop']}{day_text}, "
        f"driven by the {factor_label.lower()} factor. This is a diagnostic "
        "proxy, not a validated composite stress score."
    )

def _render_data_interpretation(df, crops):
    if df.empty:
        _interpretation("No simulation records are available.")
        return
    crop_count = df["crop"].nunique() if "crop" in df else len(crops)
    if "day" in df:
        days = pd.to_numeric(df["day"], errors="coerce").dropna()
        period = (
            f"covering simulation days {days.min():g} to {days.max():g}"
            if not days.empty else "with no valid day values"
        )
    else:
        period = "with no day column"
    missing = int(df.isna().sum().sum())
    _interpretation(
        f"The table contains {len(df):,} daily records for {crop_count} crop(s), "
        f"{period}. {missing:,} cells are blank, so check those fields before "
        "comparing or exporting the results."
    )


def _render_stress_timeline(df):
    data, _ = _modeled_factor_data(df)

    if data.empty:
        st.info("No modeled limitation-factor data is available.")
        return

    timeline = (
        data.pivot(
            index="crop",
            columns="day",
            values="_lowest_factor",
        )
        .sort_index(axis=1)
    )

    how_to_read(
        "Each cell shows the lowest configured response or availability "
        "factor for that crop and day. Lower values indicate a more "
        "limiting factor under the current model."
    )

    fig = go.Figure(
        go.Heatmap(
            z=timeline.to_numpy(),
            x=list(timeline.columns),
            y=list(timeline.index),
            zmin=0,
            zmax=1,
            colorscale=[
                [0, "#B5533C"],
                [0.5, "#C9B45B"],
                [1, "#8DBB68"],
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Day %{x}<br>"
                "Lowest modeled factor: %{z:.2f}"
                "<extra></extra>"
            ),
            colorbar={"title": "Lowest factor", "thickness": 10},
        )
    )

    plot_layout(fig, height=240)
    fig.update_layout(
        hovermode="closest",
        xaxis_title="Simulation day",
    )
    fig.update_yaxes(autorange="reversed", automargin=True)

    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption(
        "This diagnostic uses temperature, water, nutrient, VPD and canopy "
        "air-speed factors. Light influences assimilation directly and is "
        "not represented as a separate factor here. This is not a validated "
        "whole-plant stress index."
    )

def render_details(df, crops, settings):
    st.markdown("### Detailed analysis")
    tabs = st.tabs([
        "Total biomass",
        "Daily production",
        "Harvestable",
        "Stress timeline 🧪",
        "Environment",
        "Data",
    ])

    with tabs[0]:
        render_total_biomass(df)
        _render_measure_interpretation(
            df, TOTAL_BIOMASS_COLUMNS, "Total biomass", "trend"
        )
    with tabs[1]:
        render_daily_production(df)
        _render_measure_interpretation(
            df, DAILY_PRODUCTION_COLUMNS, "Daily production", "production"
        )
    with tabs[2]:
        render_harvest(df)
        _render_measure_interpretation(
            df, YIELD_COLUMNS, "Harvestable biomass", "trend"
        )
    with tabs[3]:
        _render_stress_timeline(df)
        _render_stress_interpretation(df)
    with tabs[4]:
        environment = render_environment_section(df, settings)
        if environment:
            label, column = environment
            _render_measure_interpretation(
                df, (column,), label, "environment"
            )
        else:
            _interpretation(
                "No recognized environmental data is available to interpret."
            )
    with tabs[5]:
        render_data_table(df, crops)
        _render_data_interpretation(df, crops)
