
import streamlit as st

st.set_page_config(
	page_title="Greenlab Simulator",
	page_icon="🌱",
	layout="wide",
	initial_sidebar_state="expanded",
)

from dashboard.runner import run_all_crops
from dashboard.config import MIN_SELECTED_CROPS
from dashboard.sections.details import render_details
from dashboard.sections.header import render_header
from dashboard.sections.organs import (
    render_allocation,
    render_organ_biomass_grid,
)
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

if len(settings.selected_crops) < MIN_SELECTED_CROPS:
	st.markdown("## Greenlab Simulator")
	st.info(
		f"Choose at least {MIN_SELECTED_CROPS} crops in the sidebar to begin."
	)
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

# 1. Simulation overview
with st.expander("Simulation Overview", expanded=False):
	render_header(settings, len(crops), outcome.warnings)

# 2. Crop compatibility (open by default)
with st.expander("Crop Compatibility", expanded=True):
	render_compatibility(settings, df)

# 3. Yield
# st.divider()
with st.expander("Yield", expanded=False):
	render_yields(df, crops)

# st.divider()

# 4. Organ growth
with st.expander("Organ Growth Comparison", expanded=False):
    render_organ_biomass_grid(df, crops)
    render_allocation(df, crops)

# 5. Supporting details
# st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)
with st.expander("Supporting Details & Total Biomass", expanded=False):
	render_details(df, crops, settings)

# st.markdown('<hr style="margin:0.4rem 0;">', unsafe_allow_html=True)
st.caption(
	"Greenlab Simulator · Daily crop growth research prototype. "
	"Scientific validation is pending."
)
