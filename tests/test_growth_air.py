
from copy import deepcopy
from datetime import date

import pytest

from data.models.environment import ConstantEnvironmentModel
from data.models.types import GreenhouseConfig
from data.plants import CROPS
from simulation.engine import run_simulation


START_DATE = date(2025, 1, 1)


def simulate_tomato(
    *,
    airflow_m_s=0.5,
    relative_humidity_pct=50.0,
    days=5,
):
    greenhouse = GreenhouseConfig(
        temperature_c=24.0,
        light_hours=16.0,
        irradiance_ppfd=250.0,
        airflow_m_s=airflow_m_s,
        relative_humidity_pct=relative_humidity_pct,
        start_date=START_DATE,
    )

    return run_simulation(
        crop=deepcopy(CROPS["Tomato"]),
        greenhouse=greenhouse,
        days=days,
        start_date=START_DATE,
        environment_model=ConstantEnvironmentModel(),
    )


def test_active_crop_air_profiles_match_workbook():
    tomato = CROPS["Tomato"].parameters
    assert (
        tomato.vpd_low_limit_kpa,
        tomato.vpd_opt_low_kpa,
        tomato.vpd_opt_high_kpa,
        tomato.vpd_high_limit_kpa,
        tomato.vpd_min_factor,
        tomato.airflow_low_limit_m_s,
        tomato.airflow_opt_low_m_s,
        tomato.airflow_opt_high_m_s,
        tomato.airflow_high_limit_m_s,
        tomato.airflow_min_factor,
    ) == pytest.approx(
        (0.2, 0.95, 1.58, 2.2, 0.2, 0.05, 0.5, 1.0, 1.2, 0.2)
    )

    potato = CROPS["Potato"].parameters
    assert (
        potato.vpd_low_limit_kpa,
        potato.vpd_opt_low_kpa,
        potato.vpd_opt_high_kpa,
        potato.vpd_high_limit_kpa,
        potato.vpd_min_factor,
        potato.airflow_low_limit_m_s,
        potato.airflow_opt_low_m_s,
        potato.airflow_opt_high_m_s,
        potato.airflow_high_limit_m_s,
        potato.airflow_min_factor,
    ) == pytest.approx(
        (0.2, 0.5, 1.1, 2.2, 0.2, 0.05, 0.2, 0.7, 1.2, 0.2)
    )

    sweet_potato = CROPS["Sweet potato"].parameters
    assert (
        sweet_potato.vpd_low_limit_kpa,
        sweet_potato.vpd_opt_low_kpa,
        sweet_potato.vpd_opt_high_kpa,
        sweet_potato.vpd_high_limit_kpa,
        sweet_potato.vpd_min_factor,
        sweet_potato.airflow_low_limit_m_s,
        sweet_potato.airflow_opt_low_m_s,
        sweet_potato.airflow_opt_high_m_s,
        sweet_potato.airflow_high_limit_m_s,
        sweet_potato.airflow_min_factor,
    ) == pytest.approx(
        (0.2, 0.5, 1.2, 2.2, 0.2, 0.05, 0.2, 0.7, 1.2, 0.2)
    )


def test_vpd_response_changes_actual_crop_growth():
    # For tomato at 24 C, RH 50% places VPD in the configured
    # optimal band. RH 90% lowers VPD into the low-VPD stress region.
    optimal = simulate_tomato(relative_humidity_pct=50.0)
    stressed = simulate_tomato(relative_humidity_pct=90.0)

    assert stressed["vpd_kpa"].iloc[0] < optimal["vpd_kpa"].iloc[0]
    assert stressed["vpd_factor"].iloc[0] < optimal["vpd_factor"].iloc[0]
    assert stressed["vpd_response_active"].iloc[0]
    assert (
        stressed["gross_assimilation_g_day"].iloc[0]
        < optimal["gross_assimilation_g_day"].iloc[0]
    )
    assert (
        stressed["granted_growth_g_day"].iloc[0]
        < optimal["granted_growth_g_day"].iloc[0]
    )
    assert (
        stressed["total_biomass_g"].iloc[-1]
        < optimal["total_biomass_g"].iloc[-1]
    )


def test_airflow_response_changes_actual_crop_growth():
    optimal = simulate_tomato(airflow_m_s=0.5)
    stressed = simulate_tomato(airflow_m_s=0.0)

    assert stressed["airflow_factor"].iloc[0] < optimal["airflow_factor"].iloc[0]
    assert stressed["airflow_response_active"].iloc[0]
    assert (
        stressed["gross_assimilation_g_day"].iloc[0]
        < optimal["gross_assimilation_g_day"].iloc[0]
    )
    assert (
        stressed["granted_growth_g_day"].iloc[0]
        < optimal["granted_growth_g_day"].iloc[0]
    )
    assert (
        stressed["total_biomass_g"].iloc[-1]
        < optimal["total_biomass_g"].iloc[-1]
    )


def test_co2_remains_at_fixed_reference_without_crop_profile():
    results = simulate_tomato()

    assert results["co2_ppm"].iloc[0] == pytest.approx(430.0)
    assert results["co2_factor"].iloc[0] == pytest.approx(1.0)
    assert not results["co2_response_active"].iloc[0]
