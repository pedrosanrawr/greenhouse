
from dataclasses import replace

import pytest

from data.models.generic_growth import GenericCropGrowthModel
from data.models.types import EnvironmentConditions, ResourceAvailability
from data.plants.tomato import TOMATO_PARAMETERS


def calculate_flux(
    params,
    *,
    co2_ppm=426.0,
    relative_humidity_pct=70.0,
    airflow_m_s=0.5,
    temperature_c=24.0,
):
    model = GenericCropGrowthModel()
    state = model.initialize(params)
    state._area_per_plant_m2 = 0.25

    environment = EnvironmentConditions(
        temperature_c=temperature_c,
        light_hours=16.0,
        irradiance_ppfd=250.0,
        airflow_m_s=airflow_m_s,
        solar_radiation_mj_m2_day=15.0,
        cover_par_transmittance=0.86,
        co2_ppm=co2_ppm,
        relative_humidity_pct=relative_humidity_pct,
    )

    return model.calculate_growth(
        params,
        state,
        environment,
        ResourceAvailability(
            water_factor=1.0,
            nutrient_factor=1.0,
        ),
    )


def test_unconfigured_air_responses_remain_neutral():
    flux = calculate_flux(TOMATO_PARAMETERS)

    assert flux.co2_factor == pytest.approx(1.0)
    assert flux.vpd_factor == pytest.approx(1.0)
    assert flux.airflow_factor == pytest.approx(1.0)

    assert not flux.co2_response_active
    assert not flux.vpd_response_active
    assert not flux.airflow_response_active


def test_co2_parameter_changes_gross_assimilation():
    params = replace(
        TOMATO_PARAMETERS,
        co2_k_half_ppm=300.0,  # TEST FIXTURE ONLY
    )

    low = calculate_flux(params, co2_ppm=300.0)
    high = calculate_flux(params, co2_ppm=800.0)

    assert high.co2_factor > low.co2_factor
    assert high.gross_assimilation_g_day > low.gross_assimilation_g_day
    assert high.co2_response_active


def test_vpd_parameter_changes_gross_assimilation():
    params = replace(
        TOMATO_PARAMETERS,
        vpd_low_kpa=0.8,
        vpd_high_kpa=3.0,
        vpd_min_factor=0.3,
    )

    humid = calculate_flux(
        params, temperature_c=28.0, relative_humidity_pct=70.0
    )
    dry = calculate_flux(
        params, temperature_c=28.0, relative_humidity_pct=30.0
    )

    assert dry.vpd_kpa > humid.vpd_kpa
    assert dry.vpd_factor < humid.vpd_factor
    assert dry.gross_assimilation_g_day < humid.gross_assimilation_g_day
    assert dry.vpd_response_active


def test_airflow_parameter_changes_gross_assimilation():
    params = replace(
        TOMATO_PARAMETERS,
        airflow_sensitivity=0.2,  # TEST FIXTURE ONLY
        airflow_half_saturation_m_s=0.3,
    )

    low = calculate_flux(params, airflow_m_s=0.1)
    high = calculate_flux(params, airflow_m_s=0.8)

    assert high.airflow_factor > low.airflow_factor
    assert high.gross_assimilation_g_day > low.gross_assimilation_g_day
    assert high.airflow_response_active
