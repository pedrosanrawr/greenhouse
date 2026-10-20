from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from dashboard.config import COVER_PAR_TRANSMITTANCE
from data.models.types import GreenhouseConfig
from data.plants import CROPS
from simulation.engine import run_simulation

if TYPE_CHECKING:
    from dashboard.sidebar import SidebarSettings


@dataclass
class SimulationOutcome:
    results: pd.DataFrame
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


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


def build_greenhouse(s: "SidebarSettings") -> GreenhouseConfig:
    return GreenhouseConfig(
        temperature_c=s.temperature,
        light_hours=16.0,
        irradiance_ppfd=250.0,
        airflow_m_s=s.airflow,
        water_factor=s.water_factor,
        nutrient_factor=s.nutrient_factor,
        start_date=s.start_date,
        cover_par_transmittance=COVER_PAR_TRANSMITTANCE,
    )


def run_all_crops(s: "SidebarSettings") -> SimulationOutcome:
    greenhouse = build_greenhouse(s)
    frames, warnings, errors = [], [], []

    for crop_name in s.selected_crops:
        try:
            df, configured = run_crop_simulation(
                crop_name, greenhouse, s.simulation_days, s.start_date,
                s.irrigation_l_m2_day, s.fertilizer_n_g_m2_day,
            )
        except Exception as exc:
            errors.append(f"Could not simulate {crop_name}: {exc}")
            continue

        if df.empty:
            warnings.append(f"No usable simulation results were returned for {crop_name}.")
            continue

        frames.append(df)
        missing = [
            label for attr, label in (
                ("irrigation_l_m2_day", "irrigation"),
                ("fertilizer_n_g_m2_day", "fertilizer nitrogen"),
            ) if attr not in configured
        ]
        if missing:
            warnings.append(
                f"{crop_name}: soil model does not expose support for "
                f"{', '.join(missing)}; those inputs are not applied."
            )

    if not frames:
        return SimulationOutcome(pd.DataFrame(), warnings, errors)

    all_results = convert_numeric_columns(pd.concat(frames, ignore_index=True))
    all_results = all_results.sort_values(["crop", "day"]).reset_index(drop=True)
    return SimulationOutcome(all_results, warnings, errors)