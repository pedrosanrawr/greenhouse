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
            co2_ppm=greenhouse.co2_ppm,
            relative_humidity_pct=greenhouse.relative_humidity_pct,
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

        # Average solar radiation for each calendar day across all years.
        # MM-DD grouping prevents leap years from shifting later dates.
        weather["month_day"] = weather["date"].dt.strftime("%m-%d")

        self.solar_climatology = (
            weather.groupby("month_day")[SOLAR_COLUMN].mean()
        )

        # Retain the dated records for inspection/debugging.
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

        # Use the multi-year mean for this calendar day.
        month_day = simulation_date.strftime("%m-%d")

        if month_day not in self.solar_climatology.index:
            raise ValueError(
                f"No solar climatology value for calendar day {month_day}."
            )

        mean_solar_radiation = float(
            self.solar_climatology.loc[month_day]
        )

        return EnvironmentConditions(
            temperature_c=greenhouse.temperature_c,
            light_hours=greenhouse.light_hours,
            irradiance_ppfd=greenhouse.irradiance_ppfd,
            airflow_m_s=greenhouse.airflow_m_s,
            solar_radiation_mj_m2_day=mean_solar_radiation,
            cover_par_transmittance=greenhouse.cover_par_transmittance,
            co2_ppm=greenhouse.co2_ppm,
            relative_humidity_pct=greenhouse.relative_humidity_pct,        
        )