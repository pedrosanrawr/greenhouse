"""Load and validate daily NASA POWER weather data."""

from pathlib import Path
from datetime import date

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent
WEATHER_FILE = (
    DATA_DIR / "processed" / "weather_daily_processed.csv"
)

SOLAR_COLUMN = "solar_radiation_MJ_m2_day"


def load_daily_weather() -> pd.DataFrame:
    """Load the processed daily weather dataset."""
    if not WEATHER_FILE.exists():
        raise FileNotFoundError(
            f"Weather dataset not found: {WEATHER_FILE}"
        )

    weather = pd.read_csv(WEATHER_FILE)

    required = {
        "date",
        SOLAR_COLUMN,
        "outdoor_temp_mean_C",
        "outdoor_temp_min_C",
        "outdoor_temp_max_C",
        "outdoor_relative_humidity_pct",
        "outdoor_wind_speed_m_s",
    }

    missing = required - set(weather.columns)
    if missing:
        raise ValueError(
            f"Weather dataset is missing columns: {sorted(missing)}"
        )

    weather["date"] = pd.to_datetime(
        weather["date"], errors="raise"
    ).dt.normalize()

    if weather["date"].duplicated().any():
        raise ValueError("Duplicate dates found in weather dataset.")

    if weather[list(required - {"date"})].isna().any().any():
        raise ValueError("Missing weather values found.")

    if (weather[SOLAR_COLUMN] < 0).any():
        raise ValueError("Negative solar radiation found.")

    return weather.sort_values("date").set_index("date")


def get_weather_for_date(
    weather: pd.DataFrame,
    simulation_date: date,
) -> dict:
    """Retrieve weather inputs for one simulation day."""
    day = pd.Timestamp(simulation_date)

    if day not in weather.index:
        first = weather.index.min().date()
        last = weather.index.max().date()

        raise ValueError(
            f"{day.date()} is outside the available weather "
            f"archive ({first} to {last})."
        )

    return weather.loc[day].to_dict()