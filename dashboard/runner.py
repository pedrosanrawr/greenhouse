import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from dashboard.config import COVER_PAR_TRANSMITTANCE
from data.models.compatibility import nutrient_rates
from data.models.soil import IrrigationSchedule, NutrientApplication
from data.models.types import GreenhouseConfig
from data.models.water_budget import (
    WaterAllocation,
    allocate_water_budget,
    water_requirement_mm_day,
)
from data.plants import CROPS
from simulation.engine import run_simulation
from data.models.air import DEFAULT_REFERENCE_CO2_PPM

if TYPE_CHECKING:
    from dashboard.sidebar import SidebarSettings


@dataclass
class SimulationOutcome:
    results: pd.DataFrame
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    water_allocation: WaterAllocation | None = None


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


def configure_soil_model(
    crop,
    water_mm_day,
    requirement_mm_day,
    npk_kg_ha,
    soil_texture=None,
):
    """Apply the water supply and fertilizer to this crop's soil model.

    `crop` must be a private copy, so the shared CROPS objects are never
    changed. Returns a list of warning messages (empty when all was applied).
    """
    soil = getattr(crop, "soil_model", None)
    if not (hasattr(soil, "water_balance") and hasattr(soil, "nutrient_pools")):
        return [
            "the soil model has no water balance or nutrient pools, so the "
            "water budget and fertilizer inputs are not applied."
        ]

    problems = []

    # Apply the selected texture before configuring this run's water and
    # fertilizer. set_texture() resets soil state, so it must happen first.
    if soil_texture is not None:
        set_texture = getattr(soil, "set_texture", None)
        if callable(set_texture):
            set_texture(soil_texture)
        else:
            problems.append(
                f"the soil model does not support changing texture to "
                f"{soil_texture!r}; its existing texture is retained."
            )

    # One irrigation event per day delivering this crop's share of the budget.
    soil.water_balance.irrigation = IrrigationSchedule(
        interval_days=1, amount_mm=water_mm_day
    )
    soil.nutrient_pools.application = NutrientApplication(*npk_kg_ha)

    # Let the dataset drive the simulated demand when it has verified values.
    ledger = getattr(soil, "demand_ledger", None)
    if ledger is not None:
        if requirement_mm_day is not None:
            ledger.reference_demand_mm_day = requirement_mm_day
        rates = nutrient_rates(
            crop.parameters,
            allow_unverified=True,
        )
        if rates is not None and hasattr(ledger, "set_recommended"):
            midpoints = tuple((low + high) / 2 for low, high, _ in rates.values())
            ledger.set_recommended(crop.parameters.name, midpoints)

    return problems


def build_greenhouse(s: "SidebarSettings") -> GreenhouseConfig:
    # water_factor and nutrient_factor keep their default of 1.0: the soil
    # model now calculates them from the water budget and fertilizer.
    return GreenhouseConfig(
        temperature_c=s.temperature,
        light_hours=16.0,
        irradiance_ppfd=250.0,
        airflow_m_s=s.airflow,
        co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
        relative_humidity_pct=s.relative_humidity_pct,
        start_date=s.start_date,
        cover_par_transmittance=COVER_PAR_TRANSMITTANCE,
    )


def run_all_crops(s: "SidebarSettings") -> SimulationOutcome:
    greenhouse = build_greenhouse(s)
    frames, warnings, errors = [], [], []
    # Use one consistent requirement policy for the full simulation. Many
    # current crop water bands are provisional, so allow them here while the
    # UI labels them as unverified. Missing bands still use the shared fallback.
    requirements = {
        name: water_requirement_mm_day(
            CROPS[name].parameters,
            allow_unverified=True,
        )
        for name in s.selected_crops
    }
    allocation = allocate_water_budget(
        s.water_budget_mm_day,
        requirements,
    )
    for crop_name in allocation.defaulted:
        warnings.append(
            f"{crop_name}: no usable water requirement is available; "
            "the provisional 4.0 mm/day fallback is used to split the "
            "greenhouse water budget."
        )

    for crop_name in s.selected_crops:
        try:
            # Work on a copy: configuring the soil model changes its state.
            crop = copy.deepcopy(CROPS[crop_name])
            problems = configure_soil_model(
                crop,
                allocation.supply_mm_day[crop_name],
                requirements[crop_name],
                s.fertilizer_npk,
                soil_texture=s.soil_texture,
            )
            df = normalize_results(
                run_simulation(crop, greenhouse, s.simulation_days, s.start_date),
                crop_name,
            )
        except Exception as exc:
            errors.append(f"Could not simulate {crop_name}: {exc}")
            continue

        if df.empty:
            warnings.append(
                f"No usable simulation results were returned for {crop_name}."
            )
            continue

        frames.append(df)
        for problem in problems:
            warnings.append(f"{crop_name}: {problem}")

    if not frames:
        return SimulationOutcome(pd.DataFrame(), warnings, errors, allocation)

    all_results = convert_numeric_columns(pd.concat(frames, ignore_index=True))
    all_results = all_results.sort_values(["crop", "day"]).reset_index(drop=True)
    return SimulationOutcome(all_results, warnings, errors, allocation)