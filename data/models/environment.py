"""Environment conditions for greenhouse simulations."""

from datetime import date
from pathlib import Path

import pandas as pd

from data.models.contracts import EnvironmentModel
from data.models.types import EnvironmentConditions, GreenhouseConfig


SOLAR_COLUMN = "solar_radiation_MJ_m2_day"
CONSTANT_SOLAR_TEST_VALUE = 15.0


class ConstantEnvironmentModel(EnvironmentModel):
    """Constant conditions for isolated tests, not historical simulations."""

    def conditions_for_day(
        self,
        greenhouse: GreenhouseConfig,
        day_index: int,
    ) -> EnvironmentConditions:
        return EnvironmentConditions(
            temperature_c=greenhouse.temperature_c,
            light_hours=greenhouse.light_hours,
            irradiance_ppfd=greenhouse.irradiance_ppfd,
            airflow_m_s=greenhouse.airflow_m_s,
            solar_radiation_mj_m2_day=CONSTANT_SOLAR_TEST_VALUE,
            cover_par_transmittance=greenhouse.cover_par_transmittance,
        )


class NASAEnvironmentModel(EnvironmentModel):
    """Use NASA POWER daily solar radiation for the selected simulation dates.

    Temperature remains at the configured greenhouse value in this model.
    It does not yet simulate dynamic indoor temperature.
    """

    def __init__(self, weather_path: str | Path | None = None):
        if weather_path is None:
            weather_path = (
                Path(__file__).resolve().parents[1]
                / "processed"
                / "weather_daily_processed.csv"
            )

        weather_path = Path(weather_path)

        if not weather_path.exists():
            raise FileNotFoundError(
                f"Processed NASA weather data not found: {weather_path}"
            )

        weather = pd.read_csv(weather_path)

        required_columns = {"date", SOLAR_COLUMN}
        missing = required_columns - set(weather.columns)

        if missing:
            raise ValueError(
                f"Weather file is missing columns: {sorted(missing)}"
            )

        weather["date"] = pd.to_datetime(
            weather["date"], errors="raise"
        ).dt.normalize()

        if weather["date"].duplicated().any():
            raise ValueError("Weather file contains duplicate dates.")

        if weather[SOLAR_COLUMN].isna().any():
            raise ValueError("Solar radiation contains missing values.")

        if (weather[SOLAR_COLUMN] < 0).any():
            raise ValueError("Solar radiation cannot be negative.")

        self.weather = weather.set_index("date").sort_index()

    def conditions_for_day(
        self,
        greenhouse: GreenhouseConfig,
        day_index: int,
    ) -> EnvironmentConditions:
        if day_index < 0:
            raise ValueError("day_index cannot be negative.")

        start_date = greenhouse.start_date or date.today()
        simulation_date = (
            pd.Timestamp(start_date).normalize()
            + pd.Timedelta(days=day_index)
        )

        if simulation_date not in self.weather.index:
            first_date = self.weather.index.min().date()
            last_date = self.weather.index.max().date()

            raise ValueError(
                f"No NASA weather record for {simulation_date.date()}. "
                f"Available range: {first_date} to {last_date}."
            )

        row = self.weather.loc[simulation_date]

        return EnvironmentConditions(
            temperature_c=greenhouse.temperature_c,
            light_hours=greenhouse.light_hours,
            irradiance_ppfd=greenhouse.irradiance_ppfd,
            airflow_m_s=greenhouse.airflow_m_s,
            solar_radiation_mj_m2_day=float(row[SOLAR_COLUMN]),
            cover_par_transmittance=greenhouse.cover_par_transmittance,
        )