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
    "Scenario suitability index based on crop requirements, response "
    "profiles, and selected soil texture. Water, nutrient, and soil-texture "
    "ratings are provisional; air-response profiles are also uncalibrated. "
    "This index is not a yield prediction."
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


def _fmt_optional(value):
    return "not scored" if value is None else f"{value:.2f}"


# ============================================================
# SUMMARY (left column)
# ============================================================

def _render_water_summary(result: CompatibilityResult):
    allocation = result.water_allocation
    if allocation is None or allocation.total_requirement_mm_day <= 0:
        return
    st.caption(
        f"Water: {allocation.budget_mm_day:.1f} mm/day budget against "
        f"{allocation.total_requirement_mm_day:.1f} mm/day needed "
        f"({allocation.coverage:.0%} covered)."
    )


def _render_interpretation(result: CompatibilityResult, height: int):
    """Explain what the compatibility scores say about this scenario."""
    scored = sorted(
        (crop for crop in result.crops if crop.score is not None),
        key=lambda crop: crop.score,
        reverse=True,
    )
    excluded = [crop for crop in result.crops if crop.score is None]

    if not scored:
        paragraph = (
            "No crops could be scored because verified temperature "
            "requirements are unavailable."
        )
    else:
        top = scored[0]
        weakest = scored[-1]
        if result.group_score is not None:
            fit = (
                "strong" if result.group_score >= 0.75 else
                "partial" if result.group_score >= 0.45 else "weak"
            )
            paragraph = (
                f"Overall fit is {fit} at {result.group_score:.2f} out of 1.00. "
            )
        else:
            paragraph = "A group score needs at least two scored crops. "
        paragraph += (
            f"{top.crop} is the closest match ({top.score:.2f}), while "
            f"{weakest.crop} needs the most attention ({weakest.score:.2f}). "
        )
        if result.optimal_band_overlap_c is not None:
            low, high = result.optimal_band_overlap_c
            paragraph += f"Their shared optimal temperature range is {low:g} to {high:g} °C. "
        elif result.group_score is not None:
            paragraph += "The crops do not share an optimal temperature range. "
        if excluded:
            paragraph += (
                f"{len(excluded)} crop(s) were omitted because verified "
                "temperature requirements are unavailable. "
            )
        paragraph += (
            "Scores combine the available temperature, cycle, light, water, "
            "nutrient, soil-texture, VPD, and airflow fits. Some input data "
            "and response profiles remain provisional."
        )

    with st.container(
        height=height, key="compatibility_interpretation"
    ):
        st.markdown("**Interpretation**")
        st.write(paragraph)


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
        # st.caption(
        #     f"mean {result.mean_score:.2f} · min {result.min_score:.2f}"
        # )
        # st.caption(f"weakest: {result.weakest_crop}")

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

def _render_bars(result: CompatibilityResult, height: int):
    scored = sorted(
        (c for c in result.crops if c.score is not None),
        key=lambda c: c.score,
    )  # ascending, so the best crop ends up at the top
    unscored = [c for c in result.crops if c.score is None]

    fig = go.Figure()
    # Keep unscored crops visible as named rows, with more headroom so the
    # top category label does not get clipped by Plotly.
    for crop in unscored:
        fig.add_trace(
            go.Bar(
                x=[0],
                y=[crop.crop],
                orientation="h",
                marker={"color": "rgba(0,0,0,0)"},
                text=[f"not scored: {crop.excluded_reason or 'requirements unavailable'}"],
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
                        _fmt_optional(c.light),
                        _fmt_optional(c.water),
                        _fmt_optional(c.nutrient),
                        _fmt_optional(c.soil),
                        _fmt_optional(c.vpd),
                        _fmt_optional(c.airflow),
                    ]
                    for c in scored
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Compatibility: %{x:.2f}<br>"
                    "Rank: #%{customdata[0]}<br>"
                    "Temperature fit: %{customdata[1]}<br>"
                    "Cycle fit: %{customdata[2]}<br>"
                    "Light fit: %{customdata[3]}<br>"
                    "Water fit: %{customdata[4]}<br>"
                    "Nutrient fit: %{customdata[5]}<br>"
                    "Soil fit: %{customdata[6]}<br>"
                    "VPD fit: %{customdata[7]}<br>"
                    "Air-speed fit: %{customdata[8]}"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    plot_layout(fig, height=height)
    fig.update_layout(
        hovermode="closest",
        showlegend=False,
        margin={"l": 10, "r": 30, "t": 30, "b": 10},
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
        supplied = (
            "—" if crop.water_supply_mm_day is None
            else f"{crop.water_supply_mm_day:.2f}"
        )
        needed = (
            "placeholder" if crop.water_requirement_mm_day is None
            else f"{crop.water_requirement_mm_day:.2f}"
        )

        if crop.score is None:
            rows.append({
                "Crop": crop.crop,
                "Score": "not scored",
                "Temperature": "—",
                "Cycle": "—",
                "Light": "—",
                "Water": "—",
                "Nutrients": "—",
                "Water supplied (mm/day)": supplied,
                "Water needed (mm/day)": needed,
                "Soil": "—",
                "VPD": "—",
                "Air speed": "—",
                "Note": crop.excluded_reason,
            })
            continue

        notes = list(crop.notes)
        if crop.light is None:
            notes.append(
                "light not scored (no DLI in results)"
                if not has_dli
                else "light not scored (no crop DLI data)"
            )

        rows.append({
            "Crop": crop.crop,
            "Score": _fmt(crop.score),
            "Temperature": _fmt(crop.temperature),
            "Cycle": _fmt(crop.cycle),
            "Light": _fmt_optional(crop.light),
            "Water": _fmt_optional(crop.water),
            "Nutrients": _fmt_optional(crop.nutrient),
            "Water supplied (mm/day)": supplied,
            "Water needed (mm/day)": needed,
            "Soil": _fmt_optional(crop.soil),
            "VPD": _fmt_optional(crop.vpd),
            "Air speed": _fmt_optional(crop.airflow),
            "Note": "; ".join(notes),
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
        "temperature, crop cycle, daylight, water, nutrients, soil texture, "
        "humidity-related VPD, and airflow where the required data are "
        "available. Longer bars mean a closer match to the crop's ecological "
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
            water_budget_mm_day=settings.water_budget_mm_day,
            nutrient_supply_kg_ha=settings.fertilizer_npk,
            relative_humidity_pct=settings.relative_humidity_pct,
            airflow_m_s=settings.airflow,
            soil_texture=settings.soil_texture,
        )
    except ValueError as exc:
        st.error(f"Compatibility could not be calculated: {exc}")
        return

    chart_height = 110 + 46 * max(len(result.crops), 1)

    left, chart, interpretation = st.columns([1, 2.2, 1.35])
    with left:
        _render_summary(result)
        _render_water_summary(result)
    with chart:
        _render_bars(result, chart_height)
    with interpretation:
        _render_interpretation(result, chart_height)

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
