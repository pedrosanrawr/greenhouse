# dashboard/sections/organs.py
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import plot_layout
from dashboard.config import COLORS, OLIVE, PLOT_LAYOUT, TOTAL_BIOMASS_COLUMNS
from dashboard.utils import (
    available_organ_columns,
    first_existing_column,
    format_biomass,
    safe_number,
)

CHARTS_PER_ROW = 3


# ============================================================
# ORGAN BIOMASS GRID (one horizontal bar chart per crop)
# ============================================================

def _render_crop_card(crop_df, crop_name, organ_columns):
    with st.container(border=True):
        st.markdown(f"#### {crop_name}")

        if crop_df.empty:
            st.info("No results available for this crop.")
            return

        latest = crop_df.iloc[-1]

        organ_df = pd.DataFrame(
            [
                {
                    "Organ": organ_name,
                    "Biomass": safe_number(latest[column_name]),
                }
                for column_name, organ_name in organ_columns.items()
            ]
        )

        # Hide organs with zero biomass in the final record.
        organ_df = organ_df[organ_df["Biomass"] > 0]

        if organ_df.empty:
            st.info("No positive organ biomass was recorded.")
            return

        # Smallest first so the largest bar appears at the top.
        organ_df = organ_df.sort_values("Biomass", ascending=True)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=organ_df["Biomass"],
                y=organ_df["Organ"],
                orientation="h",
                text=[f"{value:.2f}" for value in organ_df["Biomass"]],
                textposition="outside",
                cliponaxis=False,
                marker={
                    "color": [
                        COLORS.get(organ, OLIVE) for organ in organ_df["Organ"]
                    ]
                },
                hovertemplate="%{y}<br>Biomass: %{x:.3f}<extra></extra>",
            )
        )

        # Merge the custom margin into PLOT_LAYOUT first to avoid
        # passing `margin` twice to update_layout.
        layout = {
            **PLOT_LAYOUT,
            "margin": {"l": 10, "r": 45, "t": 15, "b": 45},
        }

        fig.update_layout(
            **layout,
            height=300,
            showlegend=False,
            xaxis_title="Biomass (model units)",
            yaxis_title="",
        )
        fig.update_xaxes(
            rangemode="tozero",
            showgrid=True,
            gridcolor="rgba(180,180,180,0.13)",
        )
        fig.update_yaxes(showgrid=False, automargin=True)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"organ_chart_{crop_name}",
        )

        total_col = first_existing_column(crop_df, TOTAL_BIOMASS_COLUMNS)
        if total_col:
            st.metric("Total biomass", format_biomass(latest[total_col]))


def render_organ_biomass_grid(df, selected_crops):
    organ_columns = available_organ_columns(df)

    if not organ_columns:
        st.info("No recognized organ biomass columns were found in the results.")
        return

    st.subheader("Biomass by Plant Organ")
    st.caption(
        "Each chart shows the latest recorded biomass for each organ "
        "of the corresponding crop."
    )

    for start in range(0, len(selected_crops), CHARTS_PER_ROW):
        crop_group = selected_crops[start:start + CHARTS_PER_ROW]
        containers = st.columns(CHARTS_PER_ROW)

        for container, crop_name in zip(containers, crop_group):
            with container:
                crop_df = df[df["crop"] == crop_name].sort_values("day")
                _render_crop_card(crop_df, crop_name, organ_columns)


# ============================================================
# ORGAN ALLOCATION ESTIMATE
# ============================================================

def render_allocation(df, selected_crops):
    organ_columns = available_organ_columns(df)

    if not organ_columns:
        st.info("Organ biomass columns are not available.")
        return

    crop_name = st.selectbox(
        "Crop for allocation analysis",
        options=selected_crops,
        key="allocation_crop_selector",
    )

    crop_df = df[df["crop"] == crop_name].sort_values("day").copy()

    if len(crop_df) < 2:
        st.info("At least two daily records are needed for this analysis.")
        return

    # Net change in standing biomass between days, per organ.
    increments = pd.DataFrame(
        {
            organ_name: crop_df[column].diff().fillna(0.0)
            for column, organ_name in organ_columns.items()
        }
    ).clip(lower=0)

    total_increase = increments.sum(axis=1)

    # Share of positive standing-biomass increments. This is NOT a direct
    # measurement of gross carbon/biomass allocation.
    allocation = increments.div(total_increase.replace(0, float("nan")), axis=0) * 100
    organ_names = list(increments.columns)
    allocation["day"] = crop_df["day"].values
    allocation = allocation.dropna(subset=organ_names, how="all")

    if allocation.empty:
        st.info("No positive organ biomass changes were available to plot.")
        return

    fig = go.Figure()
    for organ_name in organ_names:
        fig.add_trace(
            go.Scatter(
                x=allocation["day"],
                y=allocation[organ_name],
                mode="lines",
                stackgroup="allocation",
                name=organ_name,
                line={"color": COLORS.get(organ_name, OLIVE)},
                hovertemplate=(
                    f"{organ_name}<br>"
                    "Day: %{x}<br>"
                    "Share: %{y:.1f}%"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        xaxis_title="Simulation day",
        yaxis_title="Share of positive biomass changes (%)",
    )
    fig.update_yaxes(range=[0, 100])

    st.plotly_chart(
        plot_layout(fig, height=390),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.caption(
        "This is an estimate from changes in standing organ biomass. "
        "Senescence, harvest and transfers can affect these changes. "
        "It is not a direct measurement of gross source–sink allocation."
    )