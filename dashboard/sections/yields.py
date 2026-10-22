import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import crop_color, line_chart, plot_layout
from dashboard.config import (
    CUMULATIVE_HARVEST_COLUMNS,
    TOTAL_BIOMASS_COLUMNS,
    TOTAL_YIELD_COLUMNS,
)
from dashboard.sections.common import CHART_CONFIG, how_to_read, section_header
from dashboard.utils import first_existing_column, safe_number

HEIGHT = 260
UNIT = "g dry mass per plant"


# ============================================================
# DATA
# ============================================================

def _final_values(df, crops, yield_col, picked_col, biomass_col):
    """One row per crop with its end-of-run yield figures."""
    rows = []
    for crop in crops:
        crop_df = df[df["crop"] == crop].sort_values("day")
        if crop_df.empty:
            continue
        last = crop_df.iloc[-1]

        total_yield = safe_number(last[yield_col])
        picked = min(safe_number(last[picked_col]), total_yield) if picked_col else 0.0
        standing = max(0.0, total_yield - picked)

        # Everything the plant has produced: what is still on it plus what was picked.
        harvest_index = None
        if biomass_col:
            produced = safe_number(last[biomass_col]) + (
                safe_number(last[picked_col]) if picked_col else 0.0
            )
            if produced > 0:
                harvest_index = total_yield / produced * 100.0

        rows.append({
            "crop": crop,
            "total_g": total_yield,
            "picked_g": picked,
            "standing_g": standing,
            "harvest_index": harvest_index,
        })
    return pd.DataFrame(rows)


# ============================================================
# CHARTS
# ============================================================

def _final_yield_chart(values):
    crops = list(values["crop"])
    colors = [crop_color(c) for c in crops]
    totals = list(values["total_g"])

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=crops,
            y=list(values["picked_g"]),
            marker={"color": colors},
            customdata=totals,
            hovertemplate=(
                "<b>%{x}</b><br>Harvested: %{y:.1f} g<br>"
                "Total yield: %{customdata:.1f} g<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Bar(
            x=crops,
            y=list(values["standing_g"]),
            marker={"color": colors, "opacity": 0.45},
            customdata=totals,
            hovertemplate=(
                "<b>%{x}</b><br>Ready, still on the plant: %{y:.1f} g<br>"
                "Total yield: %{customdata:.1f} g<extra></extra>"
            ),
        )
    )
    # Totals printed above each stacked bar.
    fig.add_trace(
        go.Scatter(
            x=crops,
            y=totals,
            mode="text",
            text=[f"{value:.1f}" for value in totals],
            textposition="top center",
            hoverinfo="skip",
            cliponaxis=False,
        )
    )

    plot_layout(fig, height=HEIGHT)
    fig.update_layout(barmode="stack", showlegend=False, hovermode="closest")
    top = max(totals) if totals else 0.0
    fig.update_yaxes(title="g / plant", range=[0, top * 1.18 if top > 0 else 1])
    return fig


def _harvest_index_chart(values):
    shown = values.dropna(subset=["harvest_index"])
    crops = list(shown["crop"])
    fig = go.Figure(
        go.Bar(
            x=crops,
            y=list(shown["harvest_index"]),
            marker={"color": [crop_color(c) for c in crops]},
            text=[f"{v:.0f}%" for v in shown["harvest_index"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Harvest index: %{y:.1f}%<extra></extra>",
        )
    )
    plot_layout(fig, height=HEIGHT)
    fig.update_layout(showlegend=False, hovermode="closest")
    fig.update_yaxes(title="%", range=[0, 110])
    return fig


# ============================================================
# SECTION
# ============================================================

def render_yields(df, crops):
    # section_header(
    #     "Yield",
    #     "Dry mass per plant from the simulation. Converting to fresh weight "
    #     "per m² needs each crop's dry-matter fraction and spacing, which the "
    #     "dataset does not have yet.",
    # )

    yield_col = first_existing_column(df, TOTAL_YIELD_COLUMNS)
    if not yield_col:
        st.info("No yield column was found in the simulation output.")
        return

    picked_col = first_existing_column(df, CUMULATIVE_HARVEST_COLUMNS)
    biomass_col = first_existing_column(df, TOTAL_BIOMASS_COLUMNS)

    values = _final_values(df, crops, yield_col, picked_col, biomass_col)
    if values.empty:
        st.info("No yield results are available for the selected crops.")
        return

    col_final, col_index, col_cum = st.columns(3)

    with col_final:
        st.markdown("#### Final yield")
        how_to_read(
            "Yield at the end of the run. Solid color is mass already "
            "harvested; the lighter part is ripe mass still on the plant."
        )
        st.plotly_chart(
            _final_yield_chart(values),
            use_container_width=True,
            config=CHART_CONFIG,
        )

    with col_index:
        st.markdown("#### Harvest index")
        how_to_read(
            "The share of everything the plant produced that is harvestable. "
            "Higher means more growth ends up as usable produce."
        )
        if values["harvest_index"].notna().any():
            st.plotly_chart(
                _harvest_index_chart(values),
                use_container_width=True,
                config=CHART_CONFIG,
            )
        else:
            st.info("Harvest index needs a total biomass column.")

    with col_cum:
        st.markdown("#### Yield over time")
        how_to_read(
            "Harvested plus ripe mass day by day. It shows when each crop "
            "starts producing and how quickly yield builds."
        )
        line_chart(
            df[df["crop"].isin(crops)], yield_col, UNIT, height=HEIGHT
        )

    waiting = list(values.loc[values["total_g"] <= 0, "crop"])
    if waiting:
        st.caption(
            "No harvestable yield yet at the end of this run: "
            + ", ".join(waiting)
            + ". These crops need more days to reach their first harvest, so "
            "try a longer duration."
        )