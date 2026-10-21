import streamlit as st

st.set_page_config(
    page_title="Greenlab Simulator",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.placeholder import build_placeholder
from dashboard.runner import run_all_crops
from dashboard.sections.details import render_details
from dashboard.sections.header import render_header
from dashboard.sections.organ_compare import render_organ_compare
from dashboard.sections.ranking import (
    render_breakdown,
    render_insights,
    render_ranking,
)

from dashboard.sections.compatibility import render_compatibility

from dashboard.sections.yields import render_yields
from dashboard.sidebar import render_sidebar
from dashboard.styles import inject_styles

inject_styles()
settings = render_sidebar()

if not settings.selected_crops:
    st.markdown("## Greenlab Simulator")
    st.info("Choose one or more crops in the sidebar to begin.")
    st.stop()

with st.spinner("Calculating crop growth..."):
    outcome = run_all_crops(settings)

for message in outcome.errors:
    st.error(message)

if outcome.results.empty:
    st.warning("No simulation results were produced.")
    st.stop()

df = outcome.results
crops = [c for c in settings.selected_crops if c in df["crop"].values]
ph = build_placeholder(crops, settings.simulation_days)

render_header(settings, len(crops), outcome.warnings)
st.caption("🧪 Sections marked with this icon currently show placeholder data.")

# 1. Which crop grows best?
# col_rank, col_heat = st.columns(2)
# with col_rank:
#     render_ranking(ph.scores)
# with col_heat:
#     render_breakdown(ph.components)
render_compatibility(settings, df)
# render_insights(ph.scores, ph.yields)

# 2. Yield
st.divider()
# st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)

render_yields(ph.yields, ph.cumulative)
st.divider()

# 3. Organ growth
# st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)
render_organ_compare(ph.organs, crops)

# 4. Supporting detail (real data), including total biomass
st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)
render_details(df, crops, settings, ph.stress)

st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)
st.caption(
    "Greenlab Simulator · Daily crop growth research prototype. "
    "Scientific validation is pending."
)