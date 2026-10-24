"""Shared simulation engine for the greenhouse simulator.

The engine is intentionally small and biomass-first. Crop-specific parameters live
in plants/<crop>.py so new crops can be added without duplicating the engine.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict

import numpy as np
import pandas as pd

ORGANS = ("leaf", "stem", "root", "flower", "fruit")


@dataclass(frozen=True)
class Species:
	name: str
	t_base: float
	t_opt: float
	t_max: float
	lue: float
	extinction_k: float
	sla: float
	maintenance: Dict[str, float]
	sink_demand: Dict[str, float]
	initial_biomass: Dict[str, float]
	harvestable_organ: str
	cycle_min_days: int
	cycle_max_days: int
	first_harvest_min_days: int
	first_harvest_max_days: int
	# Realistic  s are explicitly marked in each crop file.


@dataclass(frozen=True)
class Greenhouse:
	temperature_c: float
	light_hours: float
	irradiance_ppfd: float  # µmol photons m⁻² s⁻¹
	airflow_m_s: float
	area_per_plant_m2: float = 0.25
	water_factor: float = 1.0
	nutrient_factor: float = 1.0


def temperature_response(temp: float, base: float, optimum: float, maximum: float) -> float:
	"""Smooth triangular cardinal-temperature response in [0, 1]."""
	if temp <= base or temp >= maximum:
		return 0.0
	if temp <= optimum:
		return (temp - base) / max(optimum - base, 1e-9)
	return (maximum - temp) / max(maximum - optimum, 1e-9)


def simulate(
	species: Species,
	greenhouse: Greenhouse,
	days: int = 120,
	start_date: date | None = None,
) -> pd.DataFrame:
	"""Run one crop under constant greenhouse conditions and return daily states.

	This first version simulates each crop independently; crops do not yet compete
	for shared light, water, nitrogen, or floor area.
	"""
	if days < 1:
		raise ValueError("days must be at least 1")

	start_date = start_date or date.today()
	biomass = {organ: float(species.initial_biomass.get(organ, 0.0)) for organ in ORGANS}
	reserve_g = 0.0
	rows = []

	# Convert PPFD to daily intercepted PAR energy. 4.57 mol photons per MJ is
	# a commonly used approximate conversion for PAR.
	daily_par_mj_m2 = (
		greenhouse.irradiance_ppfd
		* greenhouse.light_hours
		* 3600
		/ 1_000_000
		/ 4.57
	)
	f_temp = temperature_response(
		greenhouse.temperature_c, species.t_base, species.t_opt, species.t_max
	)
	#  : airflow is captured by the UI but has no validated crop-specific
	# response function yet. It is reported, not used to modify growth.
	f_environment = np.clip(greenhouse.water_factor, 0.0, 1.0) * np.clip(
		greenhouse.nutrient_factor, 0.0, 1.0
	)

	for day in range(days):
		total_biomass_before = sum(biomass.values())
		lai = biomass["leaf"] * species.sla / max(greenhouse.area_per_plant_m2, 1e-9)
		intercepted_fraction = 1.0 - np.exp(-species.extinction_k * max(lai, 0.0))

		# Source: daily photosynthetic biomass gain. LUE and SLA are provisional
		#  s in plants/tomato.py, not validated cultivar parameters.
		gross_assimilation = (
			species.lue
			* daily_par_mj_m2
			* intercepted_fraction
			* greenhouse.area_per_plant_m2
			* f_temp
			* f_environment
		)

		# Maintenance respiration increases with temperature; Q10=2 is a common
		# modelling approximation and is a   pending calibration.
		q10 = 2.0 ** ((greenhouse.temperature_c - 25.0) / 10.0)
		maintenance_respiration = q10 * sum(
			species.maintenance.get(organ, 0.0) * biomass[organ]
			for organ in ORGANS
		)

		# Sink demand is a simple provisional daily organ demand profile.
		# Flower/fruit demand rises after the assumed first-harvest window.
		age = day + 1
		demand = dict(species.sink_demand)
		if age < species.first_harvest_min_days:
			demand["fruit"] = 0.0
			demand["flower"] = min(demand.get("flower", 0.0), 0.01)
		elif age <= species.first_harvest_max_days:
			demand["fruit"] = demand.get("fruit", 0.0)
		total_demand = sum(max(0.0, demand.get(o, 0.0)) for o in ORGANS)

		available = max(0.0, reserve_g + gross_assimilation - maintenance_respiration)
		if total_demand > 0 and available >= total_demand:
			growth = {o: max(0.0, demand.get(o, 0.0)) for o in ORGANS}
			reserve_g = available - total_demand
			limiting_factor = "sink"
		elif total_demand > 0:
			growth = {
				o: available * max(0.0, demand.get(o, 0.0)) / total_demand
				for o in ORGANS
			}
			reserve_g = 0.0
			limiting_factor = "source"
		else:
			growth = {o: 0.0 for o in ORGANS}
			reserve_g = available
			limiting_factor = "no sink demand"

		#  : 0.5% daily leaf senescence; replace with crop/phase-specific data.
		leaf_senescence_fraction = 0.005
		for organ in ORGANS:
			biomass[organ] += growth[organ]
		biomass["leaf"] *= (1.0 - leaf_senescence_fraction)

		# Keep storage modest to avoid unrealistic unlimited reserve accumulation.
		reserve_g = min(reserve_g, 0.1 * max(sum(biomass.values()), 0.0))
		total_biomass = sum(biomass.values())
		rows.append({
			"date": start_date + timedelta(days=day),
			"day": day,
			"crop": species.name,
			"total_biomass_g": total_biomass,
			"leaf_biomass_g": biomass["leaf"],
			"stem_biomass_g": biomass["stem"],
			"root_biomass_g": biomass["root"],
			"flower_biomass_g": biomass["flower"],
			"fruit_biomass_g": biomass["fruit"],
			"lai": lai,
			"gross_assimilation_g_day": gross_assimilation,
			"maintenance_respiration_g_day": maintenance_respiration,
			"sink_demand_g_day": total_demand,
			"limiting_factor": limiting_factor,
			"temperature_factor": f_temp,
			"environment_factor": f_environment,
			"reserve_g": reserve_g,
			"airflow_m_s": greenhouse.airflow_m_s,
		})

	return pd.DataFrame(rows)
