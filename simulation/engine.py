"""Simulation engine: coordinates models and owns the daily time loop."""
from datetime import date, timedelta

import pandas as pd

from data.models.environment import ConstantEnvironmentModel
from data.models.types import GreenhouseConfig, ORGANS
from data.plants.base import CropDefinition


def run_simulation(
    crop: CropDefinition,
    greenhouse: GreenhouseConfig,
    days: int = 120,
    start_date: date | None = None,
    environment_model=None,
) -> pd.DataFrame:
    """Run a crop using its selected model implementations and return daily records.

    The engine coordinates the models, applies calculated biomass changes, updates
    state, and collects output. It does not implement crop-growth equations itself.
    """
    if days < 1:
        raise ValueError("days must be at least 1")

    start_date = start_date or greenhouse.start_date or date.today()
    environment_model = environment_model or ConstantEnvironmentModel()
    growth_model = crop.growth_model
    soil_model = crop.soil_model
    yield_model = crop.yield_model

    state = growth_model.initialize(crop.parameters)
    # Keep the baseline area-per-plant setting available to the generic growth model.
    # A future contract revision may pass area explicitly in a dedicated context object.
    state._area_per_plant_m2 = greenhouse.area_per_plant_m2
    soil_model.initialize(greenhouse)
    rows = []

    for day_index in range(days):
        environment = environment_model.conditions_for_day(greenhouse, day_index)
        resources = soil_model.resources_for_day(crop.parameters, greenhouse, day_index)
        flux = growth_model.calculate_growth(
            crop.parameters, state, environment, resources
        )

        # The engine applies model-calculated state changes; models don't own the loop.
        for organ in ORGANS:
            old_biomass = max(0.0, state.biomass_g.get(organ, 0.0))
            growth = max(0.0, flux.organ_growth_g.get(organ, 0.0))
            loss = max(0.0, flux.organ_loss_g.get(organ, 0.0))
            state.biomass_g[organ] = max(0.0, old_biomass + growth - loss)
        state.reserve_g = max(0.0, flux.reserve_after_g)
        state.development_day = day_index + 1

        yield_state = yield_model.estimate_yield(crop.parameters, state, day_index)
        total_biomass = sum(state.biomass_g.values())

        row = {
            "date": start_date + timedelta(days=day_index),
            "day": day_index,
            "crop": crop.name,
            "total_biomass_g": total_biomass,
            "leaf_biomass_g": state.biomass_g["leaf"],
            "stem_biomass_g": state.biomass_g["stem"],
            "root_biomass_g": state.biomass_g["root"],
            "flower_biomass_g": state.biomass_g["flower"],
            "fruit_biomass_g": state.biomass_g["fruit"],
            "harvestable_biomass_g": yield_state.harvestable_biomass_g,
            "yield_ready": yield_state.yield_ready,
            "lai": flux.lai,
            "gross_assimilation_g_day": flux.gross_assimilation_g_day,
            "maintenance_respiration_g_day": flux.maintenance_respiration_g_day,
            "sink_demand_g_day": flux.sink_demand_g_day,
            "limiting_factor": flux.limiting_factor,
            "temperature_factor": flux.temperature_factor,
            "environment_factor": flux.environment_factor,
            "water_factor": resources.water_factor,
            "nutrient_factor": resources.nutrient_factor,
            "reserve_g": state.reserve_g,
            "temperature_c": environment.temperature_c,
            "light_hours": environment.light_hours,
            "irradiance_ppfd": environment.irradiance_ppfd,
            "airflow_m_s": environment.airflow_m_s,
        }
        rows.append(row)

    return pd.DataFrame(rows)