"""Simulation engine: coordinates models and owns the daily time loop.

The engine is the single place that mutates crop state and the single place that
decides how much biomass each organ gains on a given day:

    available carbon = reserve + gross assimilation - maintenance respiration
    potential growth = flat daily potential from the crop definition
    granted growth   = min(potential, available carbon)         (source limit)
    organ increment  = granted growth * biomass_ratio[phase][organ]

It also enforces the "no impossible states" rules:

* living biomass, the reserve store, and the senesced pool are never negative or
  non-finite;
* tissue loss cannot exceed the biomass an organ currently holds;
* organ growth is rejected if it exceeds the assimilates actually available.
"""
import math
from datetime import date, timedelta
from typing import Dict

import pandas as pd

from data.models.environment import NASAEnvironmentModel
from data.models.types import CropParameters, CropState, GreenhouseConfig, ORGANS
from data.plants.base import CropDefinition

# Tolerate tiny floating-point rounding when checking the carbon budget.
_CARBON_EPSILON = 1e-9

# Unused assimilate is stored as reserve up to this fraction of living biomass;
# anything above is discarded (feedback inhibition). Provisional TEST VALUE.
_RESERVE_CAP_FRACTION = 0.10


def _validate_state(state: CropState, day_index: int) -> None:
    """Raise if any tracked quantity is negative or non-finite."""
    for organ in ORGANS:
        value = state.biomass_g.get(organ, 0.0)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(
                f"impossible {organ} biomass on day {day_index}: {value!r}"
            )
    if not math.isfinite(state.reserve_g) or state.reserve_g < 0.0:
        raise ValueError(f"impossible reserve on day {day_index}: {state.reserve_g!r}")
    if not math.isfinite(state.senesced_biomass_g) or state.senesced_biomass_g < 0.0:
        raise ValueError(
            f"impossible senesced biomass on day {day_index}: {state.senesced_biomass_g!r}"
        )


def _allocate_growth(
    params: CropParameters, phase: str, granted_g: float
) -> Dict[str, float]:
    """Split the day's granted growth across organs using the phase's biomass ratio."""
    ratio = params.ratio_for(phase)  # contains every organ in ORGANS, sums to 1
    return {organ: granted_g * ratio[organ] for organ in ORGANS}


def run_simulation(
    crop: CropDefinition,
    greenhouse: GreenhouseConfig,
    days: int = 120,
    start_date: date | None = None,
    environment_model=None,
) -> pd.DataFrame:
    """Run a crop using its selected model implementations and return daily records.

    The growth model supplies the source side (gross assimilation, maintenance
    respiration, tissue loss, LAI). The engine applies the sink side (phase,
    potential growth, organ split) and updates state.

    NOTE: flux.organ_growth_g, flux.reserve_after_g and params.sink_demand are no
    longer used to decide growth; the crop definition's total_biomass_g, phase
    thresholds, and biomass_ratio replace them.
    """
    if days < 1:
        raise ValueError("days must be at least 1")

    start_date = start_date or greenhouse.start_date or date.today()
    environment_model = environment_model or NASAEnvironmentModel()
    params = crop.parameters
    growth_model = crop.growth_model
    soil_model = crop.soil_model
    yield_model = crop.yield_model

    state = growth_model.initialize(params)
    # Keep the baseline area-per-plant setting available to the generic growth model.
    # A future contract revision may pass area explicitly in a dedicated context object.
    state._area_per_plant_m2 = greenhouse.area_per_plant_m2
    soil_model.initialize(greenhouse)
    rows = []

    for day_index in range(days):
        environment = environment_model.conditions_for_day(greenhouse, day_index)
        resources = soil_model.resources_for_day(params, greenhouse, day_index)
        flux = growth_model.calculate_growth(params, state, environment, resources)

        # ---- source side: carbon the plant can actually spend today
        reserve_before = max(0.0, state.reserve_g)
        available_carbon = max(
            0.0,
            reserve_before
            + max(0.0, flux.gross_assimilation_g_day)
            - max(0.0, flux.maintenance_respiration_g_day),
        )

        # ---- sink side: what the crop definition says the plant could grow today
        phase = params.phase_for_day(day_index)
        if day_index < params.growth_days:
            potential_growth = params.potential_daily_growth_g
        else:
            potential_growth = 0.0  # cycle complete: no further structural growth

        # ---- decision: grant the smaller of the two, then split by phase ratio
        granted_growth = min(potential_growth, available_carbon)
        organ_growth = _allocate_growth(params, phase, granted_growth)

        # Guard 1: growth may not exceed the assimilates actually available.
        requested_growth = sum(organ_growth.values())
        if requested_growth > available_carbon + _CARBON_EPSILON:
            raise ValueError(
                f"growth requested without available assimilates on day {day_index}: "
                f"{requested_growth:.6g} > {available_carbon:.6g}"
            )

        if potential_growth <= 0.0:
            limiting_factor = "cycle_complete"
        elif granted_growth < potential_growth - _CARBON_EPSILON:
            limiting_factor = "source"  # not enough assimilate to meet potential
        else:
            limiting_factor = "sink"  # assimilate covers potential; sink caps growth

        # ---- apply to state
        daily_loss = 0.0
        for organ in ORGANS:
            old_biomass = max(0.0, state.biomass_g.get(organ, 0.0))
            growth = organ_growth[organ]
            # Guard 2: an organ cannot lose more tissue than it currently holds.
            loss = min(max(0.0, flux.organ_loss_g.get(organ, 0.0)), old_biomass)
            state.biomass_g[organ] = max(0.0, old_biomass + growth - loss)
            # Lost tissue is tracked separately in the senesced (litter) pool.
            state.senesced_biomass_g += loss
            daily_loss += loss

        # Unspent carbon goes to the reserve, capped relative to living biomass.
        carbon_left = available_carbon - granted_growth
        reserve_cap = _RESERVE_CAP_FRACTION * sum(state.biomass_g.values())
        state.reserve_g = max(0.0, min(carbon_left, reserve_cap))
        state.development_day = day_index + 1
        _validate_state(state, day_index)

        yield_state = yield_model.estimate_yield(params, state, day_index)
        total_biomass = sum(state.biomass_g.values())

        row = {
            "date": start_date + timedelta(days=day_index),
            "day": day_index,
            "crop": crop.name,
            "phase": phase,
            "total_biomass_g": total_biomass,
            "leaf_biomass_g": state.biomass_g["leaf"],
            "stem_biomass_g": state.biomass_g["stem"],
            "root_biomass_g": state.biomass_g["root"],
            "flower_biomass_g": state.biomass_g["flower"],
            "fruit_biomass_g": state.biomass_g["fruit"],
            "root_tuber_biomass_g": state.biomass_g["root_tuber"],
            "stem_tuber_biomass_g": state.biomass_g["stem_tuber"],
            "leaf_growth_g_day": organ_growth["leaf"],
            "stem_growth_g_day": organ_growth["stem"],
            "root_growth_g_day": organ_growth["root"],
            "flower_growth_g_day": organ_growth["flower"],
            "fruit_growth_g_day": organ_growth["fruit"],
            "root_tuber_growth_g_day": organ_growth["root_tuber"],
            "stem_tuber_growth_g_day": organ_growth["stem_tuber"],
            "harvestable_biomass_g": yield_state.harvestable_biomass_g,
            "yield_ready": yield_state.yield_ready,
            "lai": flux.lai,
            "gross_assimilation_g_day": flux.gross_assimilation_g_day,
            "maintenance_respiration_g_day": flux.maintenance_respiration_g_day,
            "available_carbon_g_day": available_carbon,
            "potential_growth_g_day": potential_growth,
            "granted_growth_g_day": granted_growth,
            "sink_demand_g_day": potential_growth,  # kept so existing charts still work
            "limiting_factor": limiting_factor,
            "model_limiting_factor": flux.limiting_factor,
            "temperature_factor": flux.temperature_factor,
            "environment_factor": flux.environment_factor,
            "water_factor": resources.water_factor,
            "nutrient_factor": resources.nutrient_factor,
            "reserve_g": state.reserve_g,
            "senesced_biomass_g": state.senesced_biomass_g,
            "tissue_loss_g_day": daily_loss,
            "maintenance_deficit_g_day": flux.maintenance_deficit_g_day,
            "temperature_c": environment.temperature_c,
            "light_hours": environment.light_hours,
            "irradiance_ppfd": environment.irradiance_ppfd,
            "airflow_m_s": environment.airflow_m_s,
        }
        rows.append(row)

    return pd.DataFrame(rows)