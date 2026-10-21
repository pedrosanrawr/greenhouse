# dashboard/sections/compatibility.py
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import crop_color, plot_layout
from dashboard.sections.common import CHART_CONFIG, section_header
from data.models.compatibility import CompatibilityResult, score_run
from data.plants import CROPS

DLI_COLUMN = "dli_mol_par_m2_day"

BAND_FILL = "rgba(143,163,184,0.28)"
BAND_OPTIMAL = "#8FA3B8"
TEXT_COLOR = "#F2F2F2"
MUTED_COLOR = "#BDBDBD"

CAPTION = (
    "Scenario suitability index based on provisional ecological "
    "requirements. Not a yield prediction."
)


# ============================================================
# HELPERS
# ============================================================

def mean_run_dli(df):
    """Mean DLI of the run. Identical for every crop, so use the first."""
    if DLI_COLUMN not in df.columns or df.empty:
        return None
    first_crop = df["crop"].iloc[0]
    series = pd.to_numeric(
        df.loc[df["crop"] == first_crop, DLI_COLUMN], errors="coerce"
    ).dropna()
    return float(series.mean()) if not series.empty else None


def _fmt(value):
    return "—" if value is None else f"{value:.2f}"


# ============================================================
# SUMMARY (left column)
# ============================================================

def _render_summary(result: CompatibilityResult):
    scored = [c for c in result.crops if c.score is not None]

    if result.group_score is not None:
        st.metric(
            f"Group score ({len(scored)} crops)",
            f"{result.group_score:.2f}",
            help=(
                "0.5 x mean + 0.5 x minimum of the crop scores, so one "
                "poorly matched crop pulls the group score down."
            ),
        )
        st.caption(
            f"mean {result.mean_score:.2f} · min {result.min_score:.2f}"
        )
        st.caption(f"weakest: {result.weakest_crop}")

        if result.optimal_band_overlap_c is None:
            st.caption("No common optimal temperature range.")
        else:
            low, high = result.optimal_band_overlap_c
            st.caption(f"Optimal bands overlap at {low:g} to {high:g} °C.")
        return

    if len(scored) == 1:
        crop = scored[0]
        st.metric(f"{crop.crop} score", f"{crop.score:.2f}")
        st.caption("A group score needs at least 2 scored crops.")
        return

    st.metric("Group score", "n/a")
    st.caption("No crop could be scored. See the notes below.")


# ============================================================
# BAR CHART (right column)
# ============================================================

def _render_bars(result: CompatibilityResult):
    scored = sorted(
        (c for c in result.crops if c.score is not None),
        key=lambda c: c.score,
    )  # ascending, so the best crop ends up at the top
    unscored = [c for c in result.crops if c.score is None]

    fig = go.Figure()

    # Unscored crops sit at the bottom as labelled rows with no bar.
    for crop in unscored:
        fig.add_trace(
            go.Bar(
                x=[0],
                y=[crop.crop],
                orientation="h",
                marker={"color": "rgba(0,0,0,0)"},
                text=[f"not scored: {crop.excluded_reason}"],
                textposition="outside",
                textfont={"color": MUTED_COLOR},
                cliponaxis=False,
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if scored:
        ranks = {c.crop: i + 1 for i, c in enumerate(reversed(scored))}
        fig.add_trace(
            go.Bar(
                x=[c.score for c in scored],
                y=[c.crop for c in scored],
                orientation="h",
                marker={"color": [crop_color(c.crop) for c in scored]},
                text=[f"{c.score:.2f}" for c in scored],
                textposition="outside",
                cliponaxis=False,
                customdata=[
                    [
                        ranks[c.crop],
                        _fmt(c.temperature),
                        _fmt(c.cycle),
                        "not scored" if c.light is None else _fmt(c.light),
                    ]
                    for c in scored
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Compatibility: %{x:.2f}<br>"
                    "Rank: #%{customdata[0]}<br>"
                    "Temperature fit: %{customdata[1]}<br>"
                    "Cycle fit: %{customdata[2]}<br>"
                    "Light fit: %{customdata[3]}"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    n_rows = len(scored) + len(unscored)
    plot_layout(fig, height=90 + 46 * max(n_rows, 1))
    fig.update_layout(
        hovermode="closest",
        showlegend=False,
        margin={"l": 10, "r": 30, "t": 10, "b": 10},
    )
    fig.update_xaxes(
        range=[0, 1.12],
        tickvals=[0, 0.25, 0.5, 0.75, 1.0],
        title="Compatibility score (0 to 1)",
        showgrid=True,
        gridcolor="rgba(180,180,180,0.13)",
    )
    fig.update_yaxes(automargin=True, showgrid=False)
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


# ============================================================
# DETAILS
# ============================================================

def _render_table(result: CompatibilityResult, has_dli: bool):
    rows = []
    for crop in result.crops:
        if crop.score is None:
            rows.append({
                "Crop": crop.crop,
                "Score": "not scored",
                "Temperature": "—",
                "Cycle": "—",
                "Light": "—",
                "Note": crop.excluded_reason,
            })
            continue

        if crop.light is not None:
            note = ""
        elif not has_dli:
            note = "light not scored (no DLI in results)"
        else:
            note = "light not scored (no crop DLI data)"

        rows.append({
            "Crop": crop.crop,
            "Score": _fmt(crop.score),
            "Temperature": _fmt(crop.temperature),
            "Cycle": _fmt(crop.cycle),
            "Light": "not scored" if crop.light is None else _fmt(crop.light),
            "Note": note,
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_fit_strips(params_by_name, result, temperature_c):
    rows = [
        (crop, params_by_name[crop.crop])
        for crop in result.crops
        if crop.score is not None
    ]
    if not rows:
        st.caption("No scored crops to show.")
        return

    fig = go.Figure()
    for index, (_, params) in enumerate(rows):
        fig.add_shape(
            type="rect",
            x0=params.t_abs_min, x1=params.t_abs_max,
            y0=index - 0.28, y1=index + 0.28,
            fillcolor=BAND_FILL, line={"width": 0},
        )
        fig.add_shape(
            type="rect",
            x0=params.t_opt_min, x1=params.t_opt_max,
            y0=index - 0.28, y1=index + 0.28,
            fillcolor=BAND_OPTIMAL, line={"width": 0},
        )

    fig.add_vline(x=temperature_c, line_dash="dash", line_color=MUTED_COLOR)
    fig.add_trace(
        go.Scatter(
            x=[temperature_c] * len(rows),
            y=list(range(len(rows))),
            mode="markers",
            marker={"symbol": "triangle-down", "size": 12, "color": TEXT_COLOR},
            customdata=[
                [
                    crop.crop, params.t_abs_min, params.t_abs_max,
                    params.t_opt_min, params.t_opt_max, crop.temperature,
                ]
                for crop, params in rows
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Run temperature: %{x:g} °C<br>"
                "Tolerable range: %{customdata[1]:g} to %{customdata[2]:g} °C<br>"
                "Optimal band: %{customdata[3]:g} to %{customdata[4]:g} °C<br>"
                "Temperature score: %{customdata[5]:.2f}"
                "<extra></extra>"
            ),
        )
    )

    plot_layout(fig, height=70 + 48 * len(rows))
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
    )
    fig.update_xaxes(
        title="Run temperature (°C)",
        showgrid=True,
        gridcolor="rgba(180,180,180,0.13)",
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(rows))),
        ticktext=[crop.crop for crop, _ in rows],
        autorange="reversed",
        showgrid=False,
        automargin=True,
    )
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    st.caption(
        "Dark bar = optimal band. Light bar = tolerable range (absolute "
        "min to absolute max). Triangle and dashed line = run temperature."
    )


# ============================================================
# SECTION
# ============================================================

def render_compatibility(settings, df):
    section_header(
        "Compatibility",
        "How well each selected crop suits this greenhouse, based on "
        "temperature, run length and (when available) daylight. "
        "Longer bars mean a closer match to the crop's ecological "
        "requirements.",
    )

    # CROPS holds CropDefinition objects; the requirements live on .parameters
    params_by_name = {
        name: CROPS[name].parameters for name in settings.selected_crops
    }
    dli = mean_run_dli(df)

    try:
        result = score_run(
            params_by_name,
            settings.temperature,
            settings.simulation_days,
            dli,
        )
    except ValueError as exc:
        st.error(f"Compatibility could not be calculated: {exc}")
        return

    left, right = st.columns([1, 3])
    with left:
        _render_summary(result)
    with right:
        _render_bars(result)

    excluded = [c for c in result.crops if c.score is None]
    if excluded and result.group_score is not None:
        scored_count = len(result.crops) - len(excluded)
        st.caption(
            f"Group score covers {scored_count} of {len(result.crops)} "
            "selected crops."
        )

    with st.expander("Per-crop details"):
        _render_table(result, has_dli=dli is not None)

    with st.expander("Temperature fit"):
        _render_fit_strips(params_by_name, result, settings.temperature)

    st.caption(CAPTION)