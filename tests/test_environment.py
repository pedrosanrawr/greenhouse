
from datetime import date

import pandas as pd
import pytest

from data.models.environment import NASAEnvironmentModel, SOLAR_COLUMN
from data.models.types import GreenhouseConfig


def make_model(tmp_path, dates, solar_values):
    weather_path = tmp_path / "weather.csv"
    pd.DataFrame({
        "date": dates,
        SOLAR_COLUMN: solar_values,
    }).to_csv(weather_path, index=False)

    return NASAEnvironmentModel(weather_path)


def make_greenhouse(start_date):
    return GreenhouseConfig(
        temperature_c=24.0,
        light_hours=16.0,
        irradiance_ppfd=250.0,
        airflow_m_s=0.5,
        start_date=start_date,
    )


def test_solar_uses_mean_for_same_calendar_day_across_years(tmp_path):
    model = make_model(
        tmp_path,
        dates=[
            "2001-01-01",
            "2002-01-01",
            "2001-01-02",
            "2002-01-02",
        ],
        solar_values=[10.0, 14.0, 8.0, 12.0],
    )

    # The simulated year need not match a year present in the source file.
    greenhouse = make_greenhouse(date(2024, 1, 1))

    day_1 = model.conditions_for_day(greenhouse, 0)
    day_2 = model.conditions_for_day(greenhouse, 1)

    assert day_1.solar_radiation_mj_m2_day == pytest.approx(12.0)
    assert day_2.solar_radiation_mj_m2_day == pytest.approx(10.0)


def test_leap_day_uses_mean_of_available_leap_day_records(tmp_path):
    model = make_model(
        tmp_path,
        dates=[
            "2004-02-29",
            "2008-02-29",
        ],
        solar_values=[16.0, 20.0],
    )

    greenhouse = make_greenhouse(date(2024, 2, 29))
    result = model.conditions_for_day(greenhouse, 0)

    assert result.solar_radiation_mj_m2_day == pytest.approx(18.0)


def test_negative_day_index_is_rejected(tmp_path):
    model = make_model(
        tmp_path,
        dates=["2001-01-01"],
        solar_values=[12.0],
    )

    greenhouse = make_greenhouse(date(2024, 1, 1))

    with pytest.raises(ValueError, match="day_index"):
        model.conditions_for_day(greenhouse, -1)
