# dashboard/sections/details.py
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import plot_layout
from dashboard.sections.biomass import (
    render_daily_production,
    render_harvest,
    render_total_biomass,
)
from dashboard.sections.common import CHART_CONFIG, how_to_read
from dashboard.sections.comparison import render_data_table
from dashboard.sections.environment import render_environment_section


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
    with tabs[1]:
        render_daily_production(df)
    with tabs[2]:
        render_harvest(df)
    with tabs[3]:
        _render_stress_timeline(stress)
    with tabs[4]:
        render_environment_section(df, settings)
    with tabs[5]:
        render_data_table(df, crops)