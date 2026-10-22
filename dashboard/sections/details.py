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


def _interpretation(text):
    with st.container():
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
            f"Average daily production was {average:.2f} model units per day. "
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


def _render_stress_interpretation(stress):
    values = stress.apply(pd.to_numeric, errors="coerce")
    if values.empty or values.notna().sum().sum() == 0:
        _interpretation("No stress timeline values are available to interpret.")
        return
    mean_value = values.stack().mean()
    weakest = values.stack().idxmin()
    _interpretation(
        f"The placeholder timeline averaged {mean_value:.2f} on a 0–1 scale. "
        f"Its lowest value was {values.loc[weakest[0], weakest[1]]:.2f} for "
        f"{weakest[0]} on day {weakest[1]}. These values are illustrative "
        "and do not represent validated crop stress."
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


def _render_stress_timeline(stress):
    st.caption("🧪 Placeholder data")
    how_to_read(
        "Green days were close to ideal, red days were limited by "
        "temperature, light, water or nutrients."
    )
    fig = go.Figure(
        go.Heatmap(
            z=stress.values,
            x=list(stress.columns),
            y=list(stress.index),
            zmin=0, zmax=1,
            colorscale=[[0, "#B5533C"], [0.5, "#C9B45B"], [1, "#8DBB68"]],
            hovertemplate="<b>%{y}</b><br>Day %{x}<br>Condition: %{z:.2f}<extra></extra>",
            colorbar={"title": "1 = ideal", "thickness": 10},
        )
    )
    plot_layout(fig, height=240)
    fig.update_layout(hovermode="closest", xaxis_title="Simulation day")
    fig.update_yaxes(autorange="reversed", automargin=True)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def render_details(df, crops, settings, stress):
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
        _render_stress_timeline(stress)
        _render_stress_interpretation(stress)
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
