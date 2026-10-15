"""Tomato parameter set.

Spreadsheet source: greenhouse_crop_parameters_v1_draft.xlsm, Crop_Database,
Tomato row. Spreadsheet values are broad ecological/production references, not
validated cardinal-temperature or source-sink model parameters.
"""
from data.model import Species

TOMATO = Species(
	name="Tomato",
	# Spreadsheet: EcoCrop absolute minimum 7°C, optimum band 20–27°C,
	# absolute maximum 35°C. These are used as the first model response bounds;
	# the response curve is a simplified approximation, not a cultivar calibration.
	t_base=7.0,
	t_opt=24.0,  # TEST VALUE: midpoint of spreadsheet's 20–27°C optimal band.
	t_max=35.0,
	# TEST VALUE: light-use efficiency, g dry biomass per MJ intercepted PAR.
	lue=2.5,
	# TEST VALUE: Beer-Lambert light extinction coefficient.
	extinction_k=0.7,
	# TEST VALUE: specific leaf area, m² leaf per g leaf dry matter.
	sla=0.03,
	# TEST VALUES: organ maintenance respiration coefficients, g/g/day at 25°C.
	maintenance={
		"leaf": 0.015,
		"stem": 0.005,
		"root": 0.010,
		"flower": 0.010,
		"fruit": 0.003,
	},
	# TEST VALUES: provisional organ sink demand, g dry matter per plant per day.
	sink_demand={
		"leaf": 0.20,
		"stem": 0.12,
		"root": 0.08,
		"flower": 0.04,
		"fruit": 0.45,
	},
	# TEST VALUES: initial plant organ dry biomass, g/plant.
	initial_biomass={
		"leaf": 0.5,
		"stem": 0.2,
		"root": 0.2,
		"flower": 0.0,
		"fruit": 0.0,
	},
	harvestable_organ="fruit",
	# Spreadsheet: cycle 70–150 days; first harvest 70–130 days.
	cycle_min_days=70,
	cycle_max_days=150,
	first_harvest_min_days=70,
	first_harvest_max_days=130,
)
