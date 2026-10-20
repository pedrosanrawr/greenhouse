# dashboard/sections/ranking.py
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import crop_color, plot_layout
from dashboard.config import SCORE_BANDS
from dashboard.sections.common import CHART_CONFIG, section_header

CHART_HEIGHT = 280


def render_ranking(scores):
    section_header(
        "Compatibility ranking",
        "Longer bars mean the crop grew closer to its optimum in this "
        "greenhouse. Shaded bands show Poor, Fair, Good and Optimal.",
        placeholder=True,
    )

    ordered = scores.sort_values("score", ascending=True)
    ranks = {crop: i + 1 for i, crop in enumerate(scores["crop"])}

    fig = go.Figure()

    for label, low, high, color in SCORE_BANDS:
        fig.add_vrect(
            x0=low, x1=high, fillcolor=color, opacity=0.10,
            layer="below", line_width=0,
            annotation_text=label, annotation_position="top",
            annotation_font_size=10,
        )

    fig.add_trace(
        go.Bar(
            x=ordered["score"],
            y=ordered["crop"],
            orientation="h",
            marker={"color": [crop_color(c) for c in ordered["crop"]]},
            text=[f"{v:.0f}" for v in ordered["score"]],
            textposition="inside",
            customdata=[
                [ranks[c], b, l]
                for c, b, l in zip(ordered["crop"], ordered["band"], ordered["limiting"])
            ],
            hovertemplate=(
                "<b>%{y}</b><br>Score: %{x:.1f} / 100<br>"
                "Rank: #%{customdata[0]}<br>Rating: %{customdata[1]}<br>"
                "Main limit: %{customdata[2]}<extra></extra>"
            ),
        )
    )

    plot_layout(fig, height=CHART_HEIGHT)
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
    )
    fig.update_xaxes(range=[0, 100], title="Compatibility score")
    fig.update_yaxes(automargin=True)

    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def render_breakdown(components):
    section_header(
        "Score breakdown",
        "Each cell shows how close a crop was to optimal for one factor. "
        "Red cells explain why a crop's overall score is low.",
        placeholder=True,
    )

    fig = go.Figure(
        go.Heatmap(
            z=components.values,
            x=list(components.columns),
            y=list(components.index),
            zmin=0, zmax=100,
            colorscale=[[0, "#B5533C"], [0.5, "#C9B45B"], [1, "#8DBB68"]],
            text=components.values.round(0),
            texttemplate="%{text:.0f}",
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.0f} / 100<extra></extra>",
            colorbar={"title": "Score", "thickness": 10},
        )
    )

    plot_layout(fig, height=CHART_HEIGHT)
    fig.update_layout(
        hovermode="closest",
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
    )
    fig.update_yaxes(autorange="reversed", automargin=True)

    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


def render_insights(scores, yields):
    section_header("Key insights", placeholder=True)

    best = scores.iloc[0]
    top_yield = yields.sort_values("yield_g", ascending=False).iloc[0]

    lines = [
        f"**{best['crop']}** is the best fit, scoring {best['score']:.0f}/100 "
        f"({best['band']}).",
        f"Its weakest factor is **{best['limiting'].lower()}**.",
        f"**{top_yield['crop']}** has the highest yield "
        f"({top_yield['yield_g']:.0f} g).",
    ]
    if top_yield["crop"] != best["crop"]:
        lines.append(
            f"{top_yield['crop']} yields the most but is not the best fit."
        )

    with st.container(border=True):
        for line in lines:
            st.markdown(f"- {line}")