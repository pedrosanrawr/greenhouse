# dashboard/sections/organ_compare.py
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import plot_layout
from dashboard.config import COLORS, OLIVE
from dashboard.placeholder import ORGANS
from dashboard.sections.common import CHART_CONFIG, how_to_read, section_header

HEIGHT = 300


def _stacked(organs, crops, norm):
    fig = go.Figure()
    for organ in ORGANS:
        sub = organs[organs["organ"] == organ].set_index("crop").reindex(crops)
        fig.add_trace(
            go.Bar(
                name=organ,
                x=sub["biomass"] if norm else list(crops),
                y=list(crops) if norm else sub["biomass"],
                orientation="h" if norm else "v",
                marker={"color": COLORS.get(organ, OLIVE)},
                hovertemplate=(
                    f"<b>%{{{'y' if norm else 'x'}}}</b><br>{organ}: "
                    + ("%{x:.1f} g" if norm else "%{y:.1f} g")
                    + "<extra></extra>"
                ),
            )
        )
    plot_layout(fig, height=HEIGHT)
    fig.update_layout(barmode="stack", hovermode="closest")
    if norm:
        fig.update_layout(barnorm="percent")
        fig.update_xaxes(title="Share of total biomass (%)")
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_yaxes(title="Biomass (g)")
    return fig


def render_organ_compare(organs, crops):
    section_header("Organ growth")
    col_abs, col_pct = st.columns(2)

    with col_abs:
        st.markdown("#### Biomass by organ")
        how_to_read("Total height is total biomass. Colors show which organs hold it.")
        st.plotly_chart(_stacked(organs, crops, False), use_container_width=True, config=CHART_CONFIG)

    with col_pct:
        st.markdown("#### Biomass partitioning")
        how_to_read(
            "Each bar sums to 100%, so crops of different sizes can be "
            "compared by where they invest growth."
        )
        st.plotly_chart(_stacked(organs, crops, True), use_container_width=True, config=CHART_CONFIG)