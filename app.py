import copy

import math
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from datetime import date, timedelta
from data.models.soil import (
    SOIL_TEXTURES,
    DemandLedger,
    IrrigationSchedule,
    NutrientApplication,
    NutrientPools,
    SoilProfile,
    TextureSoilFertilizerModel,
    WaterBalance,
)
from data.models.types import GreenhouseConfig
from data.plants import CROPS
from simulation.engine import run_simulation

ORGAN_COLUMNS = {
    "leaf_biomass_g": "Leaf",
    "stem_biomass_g": "Stem",
    "root_biomass_g": "Root",
    "flower_biomass_g": "Flower",
    "fruit_biomass_g": "Fruit",
    "root_tuber_biomass_g": "Root tuber",
    "stem_tuber_biomass_g": "Stem tuber",
}
NUTRIENT_LABELS = {"n": "N (nitrogen)", "p2o5": "P₂O₅ (phosphorus)", "k2o": "K₂O (potassium)"}
NUTRIENT_DEFAULT_RATES = {"n": 100.0, "p2o5": 60.0, "k2o": 60.0}  # ASSUMPTION: placeholders, kg/ha

st.set_page_config(page_title="Greenhouse Simulator", page_icon="🌱", layout="wide")

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
	page_title="Greenlab Simulator",
	page_icon="🌱",
	layout="wide",
	initial_sidebar_state="expanded",
)

WEATHER_START_DATE = date(2001, 1, 1)
WEATHER_END_DATE = date(2025, 12, 31)
DEFAULT_SIMULATION_DAYS = 120


def build_soil_model(old_model, soil_key, irrigation_mm, interval_days, nutrient_rates):
    """Build a fresh soil model from the sidebar inputs.

    ``nutrient_rates`` maps each selected nutrient ("n", "p2o5", "k2o") to kg/ha.
    Nutrients that are not selected are not modelled and never limit growth.
    The crop's existing demand ledger (recommended rates, etc.) is reused if it has one.
    """
    profile = SoilProfile.build(soil_key)
    irrigation = IrrigationSchedule(interval_days=int(interval_days), amount_mm=float(irrigation_mm))
    application = NutrientApplication(
        nutrient_rates.get("n", 0.0),
        nutrient_rates.get("p2o5", 0.0),
        nutrient_rates.get("k2o", 0.0),
    )
    pools = NutrientPools(application, tracked=tuple(nutrient_rates))
    ledger = getattr(old_model, "demand_ledger", None) or DemandLedger()
    return TextureSoilFertilizerModel.from_components(WaterBalance(profile, irrigation), pools, ledger)


def with_soil_model(crop_definition, soil_model):
    """Copy a crop definition with a different soil model (works even if it is a frozen dataclass)."""
    clone = copy.copy(crop_definition)
    object.__setattr__(clone, "soil_model", soil_model)
    return clone


st.sidebar.title("Greenhouse Simulator")
st.sidebar.subheader("Simulation")
COVER_TYPE = "Polyethylene film, single layer"
COVER_PAR_TRANSMITTANCE = 0.860

ORGAN_COLUMNS = {
	"leaf_biomass_g": "Leaf",
	"stem_biomass_g": "Stem",
	"root_biomass_g": "Root",
	"flower_biomass_g": "Flower",
	"fruit_biomass_g": "Fruit",
	"root_tuber_biomass_g": "Root tuber",
	"stem_tuber_biomass_g": "Stem tuber",
	"leaf_biomass_g_dm_m2": "Leaf",
	"stem_biomass_g_dm_m2": "Stem",
	"root_biomass_g_dm_m2": "Root",
	"flower_biomass_g_dm_m2": "Flower",
	"fruit_biomass_g_dm_m2": "Fruit",
	"root_tuber_biomass_g_dm_m2": "Root tuber",
	"stem_tuber_biomass_g_dm_m2": "Stem tuber",
}

COLORS = {
	"Leaf": "#8DBB68",
	"Stem": "#C9B45B",
	"Root": "#A97B42",
	"Flower": "#A78BCE",
	"Fruit": "#DF8566",
	"Root tuber": "#C58B56",
	"Stem tuber": "#B2A05B",
}

OLIVE = "#8C9857"

PLOT_LAYOUT = {
	"paper_bgcolor": "rgba(0,0,0,0)",
	"plot_bgcolor": "rgba(0,0,0,0)",
	"font": {"color": "#E8E8E8", "family": "Arial"},
	"margin": {"l": 15, "r": 15, "t": 40, "b": 15},
	"legend": {
		"orientation": "h",
		"yanchor": "bottom",
		"y": 1.02,
	},
	"hovermode": "x unified",
}


# ============================================================
# STYLING
# ============================================================

st.markdown(
	"""
	<style>
		:root {
			--greenlab-olive: #8C9857;
			--greenlab-olive-dark: #737F43;
			--greenlab-olive-light: #A5B273;
			--greenlab-background: #191919;
			--greenlab-card: #292929;
			--greenlab-border: #444444;
		}

		.stApp {
			background-color: var(--greenlab-background);
		}

		[data-testid="stHeader"] {
			background-color: rgba(25, 25, 25, 0.95);
		}

		[data-testid="stSidebar"] {
			background-color: #242424;
			border-right: 1px solid #3D3D3D;
		}

		.block-container {
			padding-top: 1.6rem;
			padding-bottom: 3rem;
			max-width: 1600px;
		}

		[data-testid="stMetric"] {
			background-color: var(--greenlab-card);
			border: 1px solid var(--greenlab-border);
			padding: 16px;
			border-radius: 14px;
		}

		[data-testid="stMetricLabel"] {
			color: #BDBDBD;
		}

		[data-testid="stMetricValue"] {
			color: #F4F4F4;
		}

		[data-testid="stExpander"] {
			border: 1px solid #484848;
			border-radius: 12px;
		}

		.greenlab-subtitle {
			color: #BDBDBD;
			font-size: 0.92rem;
			margin-top: -0.5rem;
			margin-bottom: 1.2rem;
		}

		.greenlab-note {
			background-color: #242424;
			border-left: 4px solid var(--greenlab-olive);
			border-radius: 5px;
			padding: 12px 15px;
			color: #DDDDDD;
			font-size: 0.9rem;
		}

		.stButton > button[kind="primary"],
		.stFormSubmitButton > button[kind="primary"] {
			background-color: var(--greenlab-olive) !important;
			border-color: var(--greenlab-olive) !important;
			color: white !important;
		}

		.stSlider [data-baseweb="slider"] [role="slider"] {
			background-color: var(--greenlab-olive) !important;
			border-color: var(--greenlab-olive) !important;
		}

		.stSelectbox [data-baseweb="select"] > div,
		.stMultiSelect [data-baseweb="select"] > div {
			border-color: #555555;
		}

		.stSelectbox [data-baseweb="select"]:focus-within,
		.stMultiSelect [data-baseweb="select"]:focus-within {
			border-color: var(--greenlab-olive) !important;
			box-shadow: 0 0 0 1px var(--greenlab-olive) !important;
		}

		a {
			color: var(--greenlab-olive-light) !important;
		}

		hr {
			border-color: #414141;
		}
	</style>
	""",
	unsafe_allow_html=True,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def first_existing_column(df, candidates):
	for column in candidates:
		if column in df.columns:
			return column
	return None


def available_organ_columns(df):
	return {
		column: label
		for column, label in ORGAN_COLUMNS.items()
		if column in df.columns
	}


def safe_number(value, default=0.0):
	try:
		value = float(value)
		if math.isfinite(value):
			return value
	except (TypeError, ValueError):
		pass
	return default


def latest_value(series):
	if series is None or series.empty:
		return 0.0
	return safe_number(series.iloc[-1])


def format_biomass(value):
	return f"{value:,.2f}"


def plot_layout(fig, title=None, height=370):
	# Copy the defaults so that local layout changes cannot modify
	# the shared dictionary or pass the same argument twice.
	layout = {
		**PLOT_LAYOUT,
		"margin": dict(PLOT_LAYOUT["margin"]),
	}

	fig.update_layout(
		**layout,
		height=height,
		title=title,
	)

	fig.update_xaxes(
		showgrid=False,
		zeroline=False,
	)

	fig.update_yaxes(
		gridcolor="rgba(180,180,180,0.13)",
		zeroline=False,
	)

	return fig


def normalize_results(df, crop_name):
	if df is None or df.empty:
		return pd.DataFrame()

	df = df.copy()

	if "crop" not in df.columns:
		df["crop"] = crop_name

	if "day" not in df.columns:
		df["day"] = range(1, len(df) + 1)

	df["day"] = pd.to_numeric(df["day"], errors="coerce")
	df = df.dropna(subset=["day"]).sort_values("day")

	if "date" in df.columns:
		df["date"] = pd.to_datetime(df["date"], errors="coerce")

	return df


def convert_numeric_columns(df):
	"""Convert numeric-looking columns without errors='ignore'."""
	df = df.copy()

	for column in df.columns:
		if column in ("crop", "date"):
			continue

		original = df[column]
		converted = pd.to_numeric(original, errors="coerce")

		# Preserve a column as-is if it contains non-numeric text.
		original_non_missing = original.notna()
		successfully_converted = converted.notna()

		if (successfully_converted | ~original_non_missing).all():
			df[column] = converted

	return df


def configure_soil_model(crop, irrigation_l_m2_day, fertilizer_n_g_m2_day):
	"""Set inputs on the crop's soil model only when it supports those fields."""
	soil_model = getattr(crop, "soil_model", None)
	if soil_model is None:
		return []

	configured = []
	for name, value in (
		("irrigation_l_m2_day", irrigation_l_m2_day),
		("fertilizer_n_g_m2_day", fertilizer_n_g_m2_day),
	):
		if hasattr(soil_model, name):
			setattr(soil_model, name, value)
			configured.append(name)
	return configured


def run_crop_simulation(
	crop_name, greenhouse, days, start_date, irrigation_l_m2_day, fertilizer_n_g_m2_day
):
	crop = CROPS[crop_name]
	configured_soil_inputs = configure_soil_model(
		crop, irrigation_l_m2_day, fertilizer_n_g_m2_day
	)
	df = run_simulation(crop, greenhouse, days, start_date)
	return normalize_results(df, crop_name), configured_soil_inputs


def add_crop_lines(fig, df, x_column, y_column):
	for crop_name in df["crop"].dropna().unique():
		crop_df = df[df["crop"] == crop_name].sort_values(x_column)

		fig.add_trace(
			go.Scatter(
				x=crop_df[x_column],
				y=crop_df[y_column],
				mode="lines",
				name=str(crop_name),
			)
		)

	return fig


# ============================================================
# KPI CARDS
# ============================================================

def render_metric_cards(df, selected_crops, simulation_days):
	total_col = first_existing_column(
		df,
		[
			"total_biomass_g",
			"total_living_biomass_g_dm_m2",
		],
	)

	yield_col = first_existing_column(
		df,
		[
			"harvestable_biomass_g",
			"cumulative_harvested_yield_g_dm_m2",
		],
	)

	final_biomass = 0.0
	biomass_gained = 0.0
	final_harvestable = 0.0

	for crop_name in selected_crops:
		crop_df = df[df["crop"] == crop_name].sort_values("day")

		if crop_df.empty:
			continue

		if total_col:
			final_biomass += latest_value(crop_df[total_col])
			biomass_gained += (
				latest_value(crop_df[total_col])
				- safe_number(crop_df[total_col].iloc[0])
			)

		if yield_col:
			final_harvestable += latest_value(crop_df[yield_col])

	metrics = st.columns(4)

	with metrics[0]:
		st.metric(
			"Final biomass",
			format_biomass(final_biomass) if total_col else "N/A",
			help="Sum of the final biomass values for selected crops.",
		)

	with metrics[1]:
		st.metric(
			"Biomass gained",
			format_biomass(biomass_gained) if total_col else "N/A",
			help="Final minus first reported biomass, summed across crops.",
		)

	with metrics[2]:
		st.metric(
			"Harvestable biomass",
			format_biomass(final_harvestable) if yield_col else "N/A",
			help="Sum of the final values reported by the yield model.",
		)

	with metrics[3]:
		st.metric("Simulation period", f"{simulation_days} days")


# ============================================================
# TOTAL BIOMASS CHART
# ============================================================

def render_total_biomass(df):
	total_col = first_existing_column(
		df,
		[
			"total_biomass_g",
			"total_living_biomass_g_dm_m2",
		],
	)

	if not total_col:
		st.info("Total biomass is not available in the simulation output.")
		return

	fig = go.Figure()
	add_crop_lines(fig, df, "day", total_col)

	fig.update_layout(
		xaxis_title="Simulation day",
		yaxis_title="Total biomass (as reported by the model)",
	)

	st.plotly_chart(
		plot_layout(fig, height=410),
		use_container_width=True,
		config={"displayModeBar": False},
	)


# ============================================================
# HORIZONTAL ORGAN BIOMASS CHARTS
# ONE CHART PER SELECTED CROP
# ============================================================

def render_organ_biomass_grid(df, selected_crops):
	organ_columns = available_organ_columns(df)

	if not organ_columns:
		st.info(
			"No recognized organ biomass columns were found in the results."
		)
		return

	st.subheader("Biomass by Plant Organ")
	st.caption(
		"Each chart shows the latest recorded biomass for each organ "
		"of the corresponding crop."
	)

	# Two charts per row: six crops produce three rows.
	chart_columns = 2

	for start in range(0, len(selected_crops), chart_columns):
		crop_group = selected_crops[start:start + chart_columns]
		containers = st.columns(chart_columns)

		for container, crop_name in zip(containers, crop_group):
			with container:
				crop_df = (
					df[df["crop"] == crop_name]
					.sort_values("day")
				)

				with st.container(border=True):
					st.markdown(f"#### {crop_name}")

					if crop_df.empty:
						st.info("No results available for this crop.")
						continue

					latest = crop_df.iloc[-1]

					organ_data = []

					for column_name, organ_name in organ_columns.items():
						value = safe_number(latest[column_name])

						organ_data.append({
							"Organ": organ_name,
							"Biomass": value,
						})

					organ_df = pd.DataFrame(organ_data)

					# Hide organs with zero biomass in the final record.
					organ_df = organ_df[organ_df["Biomass"] > 0]

					if organ_df.empty:
						st.info("No positive organ biomass was recorded.")
						continue

					# Smallest bar first in the data so the largest
					# bar appears at the top of the horizontal chart.
					organ_df = organ_df.sort_values(
						"Biomass",
						ascending=True,
					)

					fig = go.Figure()

					fig.add_trace(
						go.Bar(
							x=organ_df["Biomass"],
							y=organ_df["Organ"],
							orientation="h",
							text=[
								f"{value:.2f}"
								for value in organ_df["Biomass"]
							],
							textposition="outside",
							cliponaxis=False,
							marker={
								"color": [
									COLORS.get(organ, OLIVE)
									for organ in organ_df["Organ"]
								]
							},
							hovertemplate=(
								"%{y}<br>"
								"Biomass: %{x:.3f}"
								"<extra></extra>"
							),
						)
					)

					# IMPORTANT:
					# Merge the custom margin into PLOT_LAYOUT first.
					# This prevents the duplicate-margin TypeError.
					layout = {
						**PLOT_LAYOUT,
						"margin": {
							"l": 10,
							"r": 45,
							"t": 15,
							"b": 45,
						},
					}

					fig.update_layout(
						**layout,
						height=max(250, 55 * len(organ_df) + 100),
						showlegend=False,
						xaxis_title="Biomass (model units)",
						yaxis_title="",
					)

					fig.update_xaxes(
						rangemode="tozero",
						showgrid=True,
						gridcolor="rgba(180,180,180,0.13)",
					)

					fig.update_yaxes(
						showgrid=False,
						automargin=True,
					)

					st.plotly_chart(
						fig,
						use_container_width=True,
						config={"displayModeBar": False},
						key=f"organ_chart_{crop_name}",
					)

					total_col = first_existing_column(
						crop_df,
						[
							"total_biomass_g",
							"total_living_biomass_g_dm_m2",
						],
					)

					if total_col:
						st.metric(
							"Total biomass",
							format_biomass(latest[total_col]),
						)


# ============================================================
# DAILY BIOMASS PRODUCTION
# ============================================================

def render_daily_production(df):
	production_col = first_existing_column(
		df,
		[
			"daily_biomass_production_g",
			"daily_biomass_production_g_dm_m2",
			"daily_biomass_increment_g",
		],
	)

	if not production_col:
		st.info(
			"Daily biomass production is not available as a separate "
			"output column yet."
		)
		return

	fig = go.Figure()
	add_crop_lines(fig, df, "day", production_col)

	fig.update_layout(
		xaxis_title="Simulation day",
		yaxis_title="Daily biomass production (model units/day)",
	)

	st.plotly_chart(
		plot_layout(fig),
		use_container_width=True,
		config={"displayModeBar": False},
	)


# ============================================================
# HARVESTABLE BIOMASS
# ============================================================

def render_harvest(df):
	yield_col = first_existing_column(
		df,
		[
			"harvestable_biomass_g",
			"cumulative_harvested_yield_g_dm_m2",
		],
	)

	if not yield_col:
		st.info(
			"No recognized harvestable-biomass or cumulative-harvest "
			"column was found."
		)
		return

	fig = go.Figure()
	add_crop_lines(fig, df, "day", yield_col)

	fig.update_layout(
		xaxis_title="Simulation day",
		yaxis_title="Harvestable biomass (model units)",
	)

	st.plotly_chart(
		plot_layout(fig),
		use_container_width=True,
		config={"displayModeBar": False},
	)


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

	crop_df = (
		df[df["crop"] == crop_name]
		.sort_values("day")
		.copy()
	)

	if crop_df.empty or len(crop_df) < 2:
		st.info("At least two daily records are needed for this analysis.")
		return

	increment_columns = {}

	for column, organ_name in organ_columns.items():
		increment_name = f"_increment_{column}"

		# Net change in standing biomass between days.
		crop_df[increment_name] = crop_df[column].diff().fillna(0.0)
		increment_columns[organ_name] = increment_name

	increments = crop_df[list(increment_columns.values())].clip(lower=0)
	total_increase = increments.sum(axis=1)

	# This is the proportion of positive standing-biomass increments.
	# It is NOT a direct measurement of gross carbon/biomass allocation.
	allocation = increments.div(
		total_increase.replace(0, float("nan")),
		axis=0,
	) * 100

	allocation.columns = list(increment_columns.keys())
	allocation["day"] = crop_df["day"].values
	allocation = allocation.dropna(
		subset=list(increment_columns.keys()),
		how="all",
	)

	if allocation.empty:
		st.info("No positive organ biomass changes were available to plot.")
		return

	fig = go.Figure()

	for organ_name in increment_columns:
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


# ============================================================
# ENVIRONMENTAL CONDITIONS
# ============================================================

def render_environment(df):
	candidates = {
		"Temperature": [
			"temperature_c",
			"temperature",
		],
		"Daily light integral": [
			"dli_mol_par_m2_day",
			"daily_light_integral",
		],
		"Intercepted PAR": [
			"intercepted_par_mol_m2_day",
		],
		"Water factor": [
			"water_factor",
			"water_availability_factor",
		],
		"Nutrient factor": [
			"nitrogen_factor",
			"nutrient_factor",
		],
		"Airflow": [
			"airflow_m_s",
			"airflow",
		],
	}

	available = {}

	for label, names in candidates.items():
		column = first_existing_column(df, names)

		if column:
			available[label] = column

	if not available:
		st.info(
			"No recognized environmental columns are available "
			"in the simulation output."
		)
		return

	variable = st.selectbox(
		"Environmental variable",
		options=list(available.keys()),
		key="environment_variable_selector",
	)

	column = available[variable]
	fig = go.Figure()

	for crop_name in df["crop"].dropna().unique():
		crop_df = df[df["crop"] == crop_name].sort_values("day")

		fig.add_trace(
			go.Scatter(
				x=crop_df["day"],
				y=crop_df[column],
				mode="lines",
				name=str(crop_name),
			)
		)

	fig.update_layout(
		xaxis_title="Simulation day",
		yaxis_title=variable,
	)

	st.plotly_chart(
		plot_layout(fig, height=350),
		use_container_width=True,
		config={"displayModeBar": False},
	)

	if variable in ("Water factor", "Nutrient factor"):
		st.caption(
			"These factors describe the model inputs or outputs. "
			"They should not be interpreted as measured plant stress "
			"unless the model defines and validates them that way."
		)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
	st.markdown("# GREENLAB")
	st.caption("Greenhouse simulation workspace")
	st.divider()

	st.subheader("1. Crop selection")

	crop_names = list(CROPS.keys())
	default_crops = ["Tomato"] if "Tomato" in crop_names else crop_names[:1]

	selected_crops = st.multiselect(
		"Crops to simulate",
		options=crop_names,
		default=default_crops,
		help="Selected crops use the same greenhouse configuration.",
	)

	if selected_crops:
		st.caption(f"{len(selected_crops)} crop(s) selected")
	else:
		st.warning("Select at least one crop.")

	st.divider()
	st.subheader("2. Greenhouse conditions")

	preset_name = st.selectbox(
		"Greenhouse preset",
		[
			"Custom",
			"Temperate greenhouse",
			"Warm greenhouse",
			"Cool greenhouse",
		],
		index=1,
	)

	preset_values = {
		"Custom": {
			"temperature": 24.0,
			"airflow": 0.5,
			"water": 1.0,
			"nutrient": 1.0,
		},
		"Temperate greenhouse": {
			"temperature": 22.0,
			"airflow": 0.5,
			"water": 1.0,
			"nutrient": 1.0,
		},
		"Warm greenhouse": {
			"temperature": 28.0,
			"airflow": 0.6,
			"water": 1.0,
			"nutrient": 1.0,
		},
		"Cool greenhouse": {
			"temperature": 18.0,
			"airflow": 0.4,
			"water": 1.0,
			"nutrient": 1.0,
		},
	}

	defaults = preset_values[preset_name]

	with st.expander("Temperature and airflow", expanded=True):
		temperature = st.slider(
			"Temperature (°C)",
			min_value=0.0,
			max_value=50.0,
			value=defaults["temperature"],
			step=0.5,
		)

		airflow = st.slider(
			"Airflow (m/s)",
			min_value=0.0,
			max_value=5.0,
			value=defaults["airflow"],
			step=0.1,
		)

	with st.expander("Soil, water and nutrients", expanded=True):
		irrigation_l_m2_day = st.number_input(
			"Irrigation (L/m²/day)", min_value=0.0, max_value=100.0,
			value=2.0, step=0.5,
			help="Applied to the crop soil model if it supports irrigation_l_m2_day.",
		)
		fertilizer_n_g_m2_day = st.number_input(
			"Fertilizer input (g N/m²/day)", min_value=0.0, max_value=100.0,
			value=0.0, step=0.1,
			help="Applied to the crop soil model if it supports fertilizer_n_g_m2_day.",
		)
		water_factor = st.slider(
			"Water availability factor", min_value=0.0, max_value=1.0,
			value=defaults["water"], step=0.05,
			help="Normalized water factor passed in GreenhouseConfig.",
		)
		nutrient_factor = st.slider(
			"Nutrient availability factor", min_value=0.0, max_value=1.0,
			value=defaults["nutrient"], step=0.05,
			help="Normalized nutrient factor passed in GreenhouseConfig.",
		)

	with st.expander("Simulation period", expanded=True):
		simulation_days = st.select_slider(
			"Duration",
			options=list(range(30, 181, 10)),
			value=DEFAULT_SIMULATION_DAYS,
			format_func=lambda value: f"{value} days",
		)

		latest_start_date = WEATHER_END_DATE - timedelta(
			days=simulation_days - 1
		)

		start_date = st.date_input(
			"Starting date",
			value=WEATHER_START_DATE,
			min_value=WEATHER_START_DATE,
			max_value=latest_start_date,
			help="The selected simulation period must fit in the configured archive.",
		)

	with st.expander("Advanced assumptions", expanded=False):
		st.text_input(
			"Greenhouse cover",
			value=COVER_TYPE,
			disabled=True,
		)

		st.number_input(
			"Cover PAR transmittance",
			min_value=0.0,
			max_value=1.0,
			value=COVER_PAR_TRANSMITTANCE,
			disabled=True,
		)

		st.caption(
			"Irrigation and fertilizer are applied only when the crop's soil "
			"model exposes matching attributes. Water and nutrient factors "
			"are passed through GreenhouseConfig."
		)

	st.divider()

	st.caption(
		"Results update automatically when settings change."
	)


# ============================================================
# MAIN DASHBOARD
# ============================================================

st.title("Greenlab Simulator")

st.markdown(
	'<p class="greenlab-subtitle">'
	'Explore crop growth, organ development and environmental '
	'responses over time.'
	'</p>',
	unsafe_allow_html=True,
)
preset_values = {
    "Custom": {"temperature": 24.0, "light_hours": 16.0, "irradiance": 250.0, "airflow": 0.5},
    "Temperate greenhouse": {"temperature": 22.0, "light_hours": 16.0, "irradiance": 250.0, "airflow": 0.5},
    "Warm greenhouse": {"temperature": 28.0, "light_hours": 16.0, "irradiance": 300.0, "airflow": 0.6},
    "Cool greenhouse": {"temperature": 18.0, "light_hours": 14.0, "irradiance": 200.0, "airflow": 0.4},
}
defaults = preset_values[preset_name]

with st.sidebar.expander("Greenhouse conditions", expanded=True):
    temperature = st.number_input("Temperature (°C)", 0.0, 50.0, defaults["temperature"], 0.5)
    light_hours = st.slider("Light period (hours/day)", 0.0, 24.0, defaults["light_hours"], 0.5)
    irradiance = st.number_input(
        "Light irradiance / PPFD (µmol/m²/s)", 0.0, 2500.0, defaults["irradiance"], 10.0
    )
    airflow = st.slider("Airflow (m/s)", 0.0, 5.0, defaults["airflow"], 0.1)
    water_factor = st.slider(
        "Water factor multiplier",
        0.0, 1.0, 1.0, 0.05,
        help="Scales the soil model's daily water factor. 1.0 = no extra restriction.",
    )
    nutrient_factor = st.slider(
        "Nutrient factor multiplier",
        0.0, 1.0, 1.0, 0.05,
        help="Scales the soil model's daily nutrient factor. 1.0 = no extra restriction.",
    )

    simulation_days = st.slider(
        "Simulation duration (days)",
        min_value=30,
        max_value=180,
        value=DEFAULT_SIMULATION_DAYS,
        step=10,
    )

    # The entire simulation must fit inside the NASA archive.
    latest_start_date = WEATHER_END_DATE - timedelta(days=simulation_days - 1)

    # Set a valid initial date and clamp saved selections to the valid range.
    if "simulation_start_date" not in st.session_state:
        st.session_state["simulation_start_date"] = DEFAULT_START_DATE

    if st.session_state["simulation_start_date"] < WEATHER_START_DATE:
        st.session_state["simulation_start_date"] = WEATHER_START_DATE

    if st.session_state["simulation_start_date"] > latest_start_date:
        st.session_state["simulation_start_date"] = latest_start_date

    start_date = st.date_input(
        "Starting date",
        min_value=WEATHER_START_DATE,
        max_value=latest_start_date,
        key="simulation_start_date",
    )

if not selected_crops:
	st.info("Choose one or more crops in the sidebar to begin.")
	st.stop()


# ============================================================
# RUN SIMULATION
# ============================================================

with st.sidebar.expander("Soil, irrigation & fertilizer", expanded=True):
    soil_key = st.selectbox(
        "Soil type",
        options=list(SOIL_TEXTURES),
        index=list(SOIL_TEXTURES).index("loam"),
        format_func=lambda k: SOIL_TEXTURES[k].name,
        help="Hydraulic properties come from Saxton & Rawls (2006) using the preset sand/clay fractions.",
    )
    _h = SoilProfile.build(soil_key).hydraulics
    st.caption(
        f"Wilting point {_h.wilting_point:.3f} · field capacity {_h.field_capacity:.3f} · "
        f"saturation {_h.saturation:.3f} m³/m³ · Ksat {_h.ksat_mm_h:.1f} mm/h"
    )

    irrigation_mm = st.number_input(
        "Irrigation amount (mm per event)", min_value=0.0, max_value=200.0, value=12.0, step=1.0
    )
    irrigation_interval = st.number_input(
        "Irrigation interval (days)", min_value=1, max_value=30, value=3, step=1
    )

    selected_nutrients = st.multiselect(
        "Nutrients to model",
        options=list(NUTRIENT_LABELS),
        default=list(NUTRIENT_LABELS),
        format_func=lambda k: NUTRIENT_LABELS[k],
        help="Selected nutrients are applied on day 0 and can limit growth. "
        "Nutrients not selected are ignored and never limit growth.",
    )
    nutrient_rates = {
        k: st.number_input(
            f"{NUTRIENT_LABELS[k]} applied (kg/ha)",
            min_value=0.0,
            max_value=1000.0,
            value=NUTRIENT_DEFAULT_RATES[k],
            step=5.0,
            key=f"rate_{k}",
        )
        for k in selected_nutrients
    }
    if not selected_nutrients:
        st.info("No nutrients selected: nutrients will not limit growth.")

greenhouse = GreenhouseConfig(
	temperature_c=temperature,
	light_hours=16.0,
	irradiance_ppfd=250.0,
	airflow_m_s=airflow,
	water_factor=water_factor,
	nutrient_factor=nutrient_factor,
	start_date=start_date,
	cover_par_transmittance=COVER_PAR_TRANSMITTANCE,
)

results = []
failed_crops = []

with st.spinner("Calculating crop growth..."):
	for crop_name in selected_crops:
		try:
			crop_df, configured_soil_inputs = run_crop_simulation(
				crop_name,
				greenhouse,
				simulation_days,
				start_date,
				irrigation_l_m2_day,
				fertilizer_n_g_m2_day,
			)

			if not crop_df.empty:
				results.append(crop_df)
				if "irrigation_l_m2_day" not in configured_soil_inputs or "fertilizer_n_g_m2_day" not in configured_soil_inputs:
					missing = []
					if "irrigation_l_m2_day" not in configured_soil_inputs:
						missing.append("irrigation")
					if "fertilizer_n_g_m2_day" not in configured_soil_inputs:
						missing.append("fertilizer nitrogen")
					st.warning(
						f"{crop_name}: soil model does not expose support for "
						f"{', '.join(missing)}; those inputs are not applied."
					)
			else:
				failed_crops.append(crop_name)

		except Exception as exc:
			failed_crops.append(crop_name)
			st.error(f"Could not simulate {crop_name}: {exc}")

if not results:
	st.warning(
		"No simulation results were produced. Check the crop definitions "
		"and simulation engine."
	)
	st.stop()

all_results = pd.concat(results, ignore_index=True)
all_results = convert_numeric_columns(all_results)

all_results = (
	all_results
	.sort_values(["crop", "day"])
	.reset_index(drop=True)
)

for crop_name in failed_crops:
	st.warning(f"No usable simulation results were returned for {crop_name}.")


# ============================================================
# DASHBOARD HEADER AND KPIS
# ============================================================

header_left, header_right = st.columns([3, 1])

with header_left:
	st.subheader("Simulation overview")
	st.caption(
		f"{len(results)} crop(s) simulated · "
		f"{simulation_days} days · "
		f"Starting {start_date.isoformat()}"
	)

with header_right:
	st.caption(f"Preset: {preset_name}")
	st.caption(f"Cover: {COVER_TYPE}")

render_metric_cards(
	all_results,
	[crop for crop in selected_crops if crop in all_results["crop"].values],
	simulation_days,
)

st.divider()


# ============================================================
# 1. OVERALL BIOMASS
# ============================================================

st.subheader("Total Biomass Growth")
st.caption(
	"Follow total reported biomass across the selected crops."
)

render_total_biomass(all_results)


# ============================================================
# 2. ORGAN BIOMASS — HORIZONTAL BAR CHARTS
# ============================================================

st.divider()

render_organ_biomass_grid(
	all_results,
	[crop for crop in selected_crops if crop in all_results["crop"].values],
)


# ============================================================
# 3. DAILY PRODUCTION AND HARVESTABLE BIOMASS
# ============================================================

st.divider()
st.subheader("Growth and Harvest Trends")

growth_column, harvest_column = st.columns(2)

with growth_column:
	st.markdown("#### Daily Biomass Production")
	render_daily_production(all_results)

with harvest_column:
	st.markdown("#### Harvestable Biomass")
	render_harvest(all_results)


# ============================================================
# 4. ORGAN ALLOCATION ESTIMATE
# ============================================================

st.divider()
st.subheader("Organ Allocation Over Time")

render_allocation(
	all_results,
	[crop for crop in selected_crops if crop in all_results["crop"].values],
)


# ============================================================
# 5. ENVIRONMENT
# ============================================================

st.divider()
st.subheader("Greenhouse Conditions and Stress Factors")

environment_metrics = st.columns(4)

with environment_metrics[0]:
	st.metric("Temperature", f"{temperature:.1f} °C")

with environment_metrics[1]:
	st.metric("Airflow", f"{airflow:.1f} m/s")

with environment_metrics[2]:
	st.metric("Water availability", f"{water_factor:.2f}")

with environment_metrics[3]:
	st.metric("Nutrient availability", f"{nutrient_factor:.2f}")

render_environment(all_results)


# ============================================================
# 6. CROP COMPARISON
# ============================================================

st.divider()
st.subheader("Crop Comparison")

total_col = first_existing_column(
	all_results,
	[
		"total_biomass_g",
		"total_living_biomass_g_dm_m2",
	],
)

yield_col = first_existing_column(
	all_results,
	[
		"harvestable_biomass_g",
		"cumulative_harvested_yield_g_dm_m2",
	],
)

if total_col:
	fig = go.Figure()

	for crop_name in selected_crops:
		crop_df = (
			all_results[all_results["crop"] == crop_name]
			.sort_values("day")
		)

		if crop_df.empty:
			continue

		fig.add_trace(
			go.Scatter(
				x=crop_df["day"],
				y=crop_df[total_col],
				mode="lines",
				name=crop_name,
			)
		)

	fig.update_layout(
		xaxis_title="Simulation day",
		yaxis_title="Total biomass (as reported by the model)",
	)

	st.plotly_chart(
		plot_layout(fig, height=420),
		use_container_width=True,
		config={"displayModeBar": False},
	)

summary_rows = []

for crop_name in selected_crops:
    base_crop = CROPS[crop_name]
    soil_model = build_soil_model(
        base_crop.soil_model, soil_key, irrigation_mm, irrigation_interval, nutrient_rates
    )
    results.append(
        run_simulation(with_soil_model(base_crop, soil_model), greenhouse, simulation_days, start_date)
    )
all_results = pd.concat(results, ignore_index=True) if results else pd.DataFrame()

overview_tab, charts_tab, details_tab = st.tabs(["Overview", "Charts", "Daily data"])

with overview_tab:
    st.subheader("Simulation setup")
    col1, col2, col3 = st.columns(3)
    col1.metric("Selected crops", len(selected_crops))
    col2.metric("Temperature", f"{temperature:.1f} °C")
    col3.metric("Light period", f"{light_hours:g} hours/day")
    st.write("**Crops:** " + (", ".join(selected_crops) if selected_crops else "None selected"))
    st.write(f"**Greenhouse preset:** {preset_name}")
    st.write(f"**Start date:** {start_date.isoformat()}")
    st.write(f"**Simulation duration:** {simulation_days} days")
    st.write("**Growth model:** Generic biomass growth")
    st.write(
        f"**Soil/fertilizer model:** TextureSoilFertilizerModel, {SOIL_TEXTURES[soil_key].name}, "
        f"irrigation {irrigation_mm:g} mm every {int(irrigation_interval)} day(s)"
    )
    if nutrient_rates:
        st.write(
            "**Fertilizer applied (day 0):** "
            + ", ".join(f"{NUTRIENT_LABELS[k]} {v:g} kg/ha" for k, v in nutrient_rates.items())
        )
    else:
        st.write("**Fertilizer applied:** none modelled (nutrients do not limit growth)")
    st.write("**Yield model:** Generic harvestable-biomass estimate")
    st.warning(
        "This is a structural baseline, not a validated agronomic predictor. "
        "Tomato parameters marked TEST VALUE are provisional. The texture-based "
        "soil model uses placeholder root-zone depth and demand figures "
        "(marked ASSUMPTION in the code), and crop demand uses fallback "
        "figures rather than the engine's actual uptake. The yield model does "
        "not remove harvested biomass from the plant."
    )

with charts_tab:
    st.subheader("Charts")
    if not all_results.empty:
        st.markdown("**Overall biomass**")
        total_chart = all_results.pivot(index="day", columns="crop", values="total_biomass_g")
        st.line_chart(total_chart, y_label="Total dry biomass (g/plant)", x_label="Day")

        st.markdown("**Biomass by organ**")
        crop_for_organs = st.selectbox("Crop to inspect", selected_crops)
        chart_style = st.radio("Chart style", ["Stacked", "Lines"], horizontal=True)

        organ_rows = all_results[all_results["crop"] == crop_for_organs].set_index("day")
        organ_chart = organ_rows[list(ORGAN_COLUMNS)].rename(columns=ORGAN_COLUMNS)
        organ_chart = organ_chart.loc[:, (organ_chart > 0).any()]

        if chart_style == "Stacked":
            st.area_chart(organ_chart, y_label="Dry biomass (g/plant)", x_label="Day")
        else:
            st.line_chart(organ_chart, y_label="Dry biomass (g/plant)", x_label="Day")

        st.markdown("**Harvestable biomass estimate**")
        yield_chart = all_results.pivot(index="day", columns="crop", values="harvestable_biomass_g")
        st.line_chart(yield_chart, y_label="Estimated harvestable biomass (g/plant)", x_label="Day")

        st.markdown("**Soil water factor**")
        water_chart = all_results.pivot(index="day", columns="crop", values="water_factor")
        st.line_chart(water_chart, y_label="Water factor (0-1)", x_label="Day")

        st.markdown("**Soil nutrient factor**")
        nutrient_chart = all_results.pivot(index="day", columns="crop", values="nutrient_factor")
        st.line_chart(nutrient_chart, y_label="Nutrient factor (0-1)", x_label="Day")
    else:
        st.info("Select Tomato in the sidebar to display simulation charts.")

with details_tab:
    st.subheader("Daily simulation data")
    if not all_results.empty:
        st.dataframe(all_results, use_container_width=True, hide_index=True)
        st.download_button(
            "Download simulation results (CSV)",
            all_results.to_csv(index=False).encode("utf-8"),
            file_name="greenhouse_simulation.csv",
            mime="text/csv",
        )
    else:
        st.info("No simulation results yet.")

st.divider()
st.caption("This is a simplified research prototype. Model contracts can be implemented by crop-specific models later.")
	crop_df = (
		all_results[all_results["crop"] == crop_name]
		.sort_values("day")
	)

	if crop_df.empty:
		continue

	row = {
		"Crop": crop_name,
		"Days simulated": int(crop_df["day"].nunique()),
	}

	if total_col:
		row["Final biomass"] = latest_value(crop_df[total_col])

	if yield_col:
		row["Final harvestable biomass"] = latest_value(crop_df[yield_col])

	summary_rows.append(row)

if summary_rows:
	st.markdown("#### Final crop values")

	st.dataframe(
		pd.DataFrame(summary_rows),
		use_container_width=True,
		hide_index=True,
	)

st.caption(
	"Comparisons are most meaningful when crops use compatible units, "
	"starting conditions and model definitions."
)


# ============================================================
# 7. DAILY SIMULATION DATA
# ============================================================

st.divider()
st.subheader("Daily Simulation Data")

with st.expander("View daily records and export data", expanded=False):
	data_crop = st.selectbox(
		"Filter by crop",
		options=["All crops"] + selected_crops,
		key="daily_data_crop_filter",
	)

	if data_crop == "All crops":
		display_df = all_results.copy()
	else:
		display_df = all_results[
			all_results["crop"] == data_crop
		].copy()

	st.dataframe(
		display_df,
		use_container_width=True,
		hide_index=True,
		height=450,
	)

	st.download_button(
		"Download daily data (CSV)",
		data=all_results.to_csv(index=False).encode("utf-8"),
		file_name="greenlab_simulation_results.csv",
		mime="text/csv",
	)

	st.caption(
		"The downloaded CSV contains all successfully simulated crops, "
		"regardless of the current table filter."
	)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
	"Greenlab Simulator · Daily crop growth research prototype. "
	"Scientific validation is pending."
)
