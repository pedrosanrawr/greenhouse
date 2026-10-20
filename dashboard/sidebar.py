from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from data.plants import CROPS
from dashboard.config import (
	COVER_PAR_TRANSMITTANCE,
	COVER_TYPE,
	DEFAULT_SIMULATION_DAYS,
	GREENHOUSE_PRESETS,
	WEATHER_END_DATE,
	WEATHER_START_DATE,
)


@dataclass
class SidebarSettings:
	selected_crops: list
	preset_name: str
	temperature: float
	airflow: float
	irrigation_l_m2_day: float
	fertilizer_n_g_m2_day: float
	water_factor: float
	nutrient_factor: float
	simulation_days: int
	start_date: date


def render_sidebar() -> SidebarSettings:
	with st.sidebar:
		st.markdown("# GREENLAB")
		st.caption("Greenhouse simulation workspace")
		st.divider()

		# ---- 1. Crop selection ----
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

		# ---- 2. Greenhouse conditions ----
		st.subheader("2. Greenhouse conditions")

		preset_name = st.selectbox(
			"Greenhouse preset",
			list(GREENHOUSE_PRESETS.keys()),
			index=1,
		)
		defaults = GREENHOUSE_PRESETS[preset_name]

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
				"Irrigation (L/m²/day)",
				min_value=0.0,
				max_value=100.0,
				value=2.0,
				step=0.5,
				help="Applied to the crop soil model if it supports irrigation_l_m2_day.",
			)
			fertilizer_n_g_m2_day = st.number_input(
				"Fertilizer input (g N/m²/day)",
				min_value=0.0,
				max_value=100.0,
				value=0.0,
				step=0.1,
				help="Applied to the crop soil model if it supports fertilizer_n_g_m2_day.",
			)
			water_factor = st.slider(
				"Water availability factor",
				min_value=0.0,
				max_value=1.0,
				value=defaults["water"],
				step=0.05,
				help="Normalized water factor passed in GreenhouseConfig.",
			)
			nutrient_factor = st.slider(
				"Nutrient availability factor",
				min_value=0.0,
				max_value=1.0,
				value=defaults["nutrient"],
				step=0.05,
				help="Normalized nutrient factor passed in GreenhouseConfig.",
			)

		with st.expander("Simulation period", expanded=True):
			simulation_days = st.select_slider(
				"Duration",
				options=list(range(30, 181, 10)),
				value=DEFAULT_SIMULATION_DAYS,
				format_func=lambda value: f"{value} days",
			)

			latest_start_date = WEATHER_END_DATE - timedelta(days=simulation_days - 1)

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
		st.caption("Results update automatically when settings change.")

	return SidebarSettings(
		selected_crops=selected_crops,
		preset_name=preset_name,
		temperature=temperature,
		airflow=airflow,
		irrigation_l_m2_day=irrigation_l_m2_day,
		fertilizer_n_g_m2_day=fertilizer_n_g_m2_day,
		water_factor=water_factor,
		nutrient_factor=nutrient_factor,
		simulation_days=simulation_days,
		start_date=start_date,
	)