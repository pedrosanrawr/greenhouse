# dashboard/charts.py
import plotly.graph_objects as go
import streamlit as st

from dashboard.config import PLOT_LAYOUT

from data.plants import CROPS
from dashboard.config import CROP_PALETTE, PLOT_LAYOUT


def plot_layout(fig, title=None, height=370):
    layout = {
        **PLOT_LAYOUT,
        "margin": dict(PLOT_LAYOUT["margin"]),
    }
    fig.update_layout(**layout, height=height, title=title)
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(180,180,180,0.13)", zeroline=False)
    return fig


def crop_color(name):
    names = list(CROPS.keys())
    index = names.index(name) if name in names else 0
    return CROP_PALETTE[index % len(CROP_PALETTE)]

def add_crop_lines(fig, df, x_column, y_column):
    for crop_name in df["crop"].dropna().unique():
        crop_df = df[df["crop"] == crop_name].sort_values(x_column)
        fig.add_trace(
            go.Scatter(
                x=crop_df[x_column],
                y=crop_df[y_column],
                mode="lines",
                name=str(crop_name),
                line={"color": crop_color(crop_name)},
            )
        )
    return fig


def line_chart(df, y_column, y_title, height=370):
    fig = go.Figure()
    add_crop_lines(fig, df, "day", y_column)
    fig.update_layout(xaxis_title="Simulation day", yaxis_title=y_title)
    st.plotly_chart(
        plot_layout(fig, height=height),
        use_container_width=True,
        config={"displayModeBar": False},
    )