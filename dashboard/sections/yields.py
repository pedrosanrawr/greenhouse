# dashboard/sections/yields.py
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import crop_color, plot_layout
from dashboard.sections.common import CHART_CONFIG, how_to_read, section_header

HEIGHT = 260


def _bar(crops, values, hover, y_title):
    fig = go.Figure(
        go.Bar(
            x=crops,
            y=values,
            marker={"color": [crop_color(c) for c in crops]},
            hovertemplate=hover,
        )
    )
    plot_layout(fig, height=HEIGHT)
    fig.update_layout(showlegend=False, hovermode="closest")
    fig.update_yaxes(title=y_title)
    return fig


def render_yields(yields, cumulative):
    section_header("Yield", placeholder=True)
    
    col_final, col_index, col_cum = st.columns(3)

    with col_final:
        st.markdown("#### Final harvestable yield")
        how_to_read("Total harvestable biomass at the end of the simulation.")
        fig = _bar(
            list(yields["crop"]), list(yields["yield_g"]),
            "<b>%{x}</b><br>Yield: %{y:.1f} g<extra></extra>", "g",
        )
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    with col_index:
        st.markdown("#### Harvest index")
        how_to_read(
            "The share of total biomass that is harvestable. Higher means "
            "more growth ends up as usable produce."
        )
        fig = _bar(
            list(yields["crop"]), list(yields["harvest_index"]),
            "<b>%{x}</b><br>Harvest index: %{y:.0f}%<extra></extra>", "%",
        )
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    with col_cum:
        st.markdown("#### Cumulative yield")
        how_to_read(
            "Shows when each crop starts producing and how quickly yield builds."
        )
        fig = go.Figure()
        for crop in yields["crop"]:
            sub = cumulative[cumulative["crop"] == crop]
            fig.add_trace(
                go.Scatter(
                    x=sub["day"], y=sub["yield_g"], mode="lines", name=crop,
                    line={"color": crop_color(crop)},
                )
            )
        plot_layout(fig, height=HEIGHT)
        fig.update_layout(xaxis_title="Simulation day", yaxis_title="g")
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)