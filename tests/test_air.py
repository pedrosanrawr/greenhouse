
import pytest

from data.models.air import (
    DEFAULT_REFERENCE_CO2_PPM,
    calculate_air_diagnostics,
    calculate_vpd_kpa,
    co2_response_factor,
    airflow_response_factor,
    vpd_response_factor,
)


# ============================================================
# VPD CALCULATION
# ============================================================

def test_vpd_is_zero_at_saturation():
    assert calculate_vpd_kpa(25.0, 100.0) == pytest.approx(0.0)


def test_vpd_increases_as_relative_humidity_decreases():
    humid = calculate_vpd_kpa(25.0, 80.0)
    dry = calculate_vpd_kpa(25.0, 40.0)

    assert dry > humid


def test_vpd_increases_with_temperature_at_fixed_humidity():
    cool = calculate_vpd_kpa(18.0, 70.0)
    warm = calculate_vpd_kpa(28.0, 70.0)

    assert warm > cool


def test_vpd_expected_value():
    # At 25 C and 50% relative humidity, VPD is approximately 1.584 kPa.
    assert calculate_vpd_kpa(25.0, 50.0) == pytest.approx(
        1.584, abs=0.002
    )


@pytest.mark.parametrize("rh", [-1.0, 100.1, float("nan")])
def test_invalid_relative_humidity_is_rejected(rh):
    with pytest.raises(ValueError):
        calculate_vpd_kpa(25.0, rh)


# ============================================================
# CO2 RESPONSE
# ============================================================

def test_co2_response_is_one_at_reference():
    factor = co2_response_factor(
        co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
        k_half_ppm=300.0,
    )

    assert factor == pytest.approx(1.0)


def test_co2_response_increases_above_reference():
    reference = co2_response_factor(
        co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
        k_half_ppm=300.0,
    )
    elevated = co2_response_factor(
        co2_ppm=800.0,
        k_half_ppm=300.0,
    )

    assert elevated > reference


def test_invalid_co2_response_parameter_is_rejected():
    with pytest.raises(ValueError):
        co2_response_factor(
            co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
            k_half_ppm=0.0,
        )


# ============================================================
# AIR DIAGNOSTICS
# ============================================================

def test_air_diagnostics_calculates_vpd_and_preserves_inputs():
    result = calculate_air_diagnostics(
        temperature_c=25.0,
        co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
        relative_humidity_pct=70.0,
        airflow_m_s=0.5,
    )

    assert result.vpd_kpa == pytest.approx(0.950, abs=0.003)
    assert result.co2_ppm == DEFAULT_REFERENCE_CO2_PPM
    assert result.relative_humidity_pct == 70.0
    assert result.airflow_m_s == 0.5


def test_negative_airflow_is_rejected():
    with pytest.raises(ValueError):
        calculate_air_diagnostics(
            temperature_c=25.0,
            co2_ppm=DEFAULT_REFERENCE_CO2_PPM,
            relative_humidity_pct=70.0,
            airflow_m_s=-0.1,
        )


# ============================================================
# VPD RESPONSE
# ============================================================

def test_vpd_factor_is_neutral_without_crop_parameters():
    assert vpd_response_factor(0.8) == pytest.approx(1.0)


# Illustrative test values only; these are not validated
# crop-specific parameters for use in the simulation.
VPD_TEST_PROFILE = {
    "low_limit_kpa": 0.2,
    "opt_low_kpa": 0.5,
    "opt_high_kpa": 1.2,
    "high_limit_kpa": 2.2,
    "min_factor": 0.5,
}


def test_vpd_factor_is_one_inside_optimal_band():
    assert vpd_response_factor(
        0.8, **VPD_TEST_PROFILE
    ) == pytest.approx(1.0)


def test_vpd_factor_penalizes_low_vpd():
    assert vpd_response_factor(
        0.35, **VPD_TEST_PROFILE
    ) == pytest.approx(0.75)


def test_vpd_factor_penalizes_high_vpd():
    assert vpd_response_factor(
        1.7, **VPD_TEST_PROFILE
    ) == pytest.approx(0.75)


@pytest.mark.parametrize("vpd", [0.2, 2.2, 0.0, 3.0])
def test_vpd_factor_reaches_floor_at_stress_limits(vpd):
    assert vpd_response_factor(
        vpd, **VPD_TEST_PROFILE
    ) == pytest.approx(0.5)


def test_partial_vpd_parameters_are_rejected():
    with pytest.raises(ValueError):
        vpd_response_factor(
            0.8,
            low_limit_kpa=0.2,
        )


# ============================================================
# AIRFLOW RESPONSE
# ============================================================

def test_airflow_factor_is_neutral_without_crop_parameters():
    assert airflow_response_factor(0.5) == pytest.approx(1.0)


# Illustrative test values only; these are not validated
# crop-specific parameters for use in the simulation.
AIRFLOW_TEST_PROFILE = {
    "low_limit_m_s": 0.0,
    "opt_low_m_s": 0.2,
    "opt_high_m_s": 0.8,
    "high_limit_m_s": 1.5,
    "min_factor": 0.5,
}


def test_airflow_factor_is_one_inside_optimal_band():
    assert airflow_response_factor(
        0.5, **AIRFLOW_TEST_PROFILE
    ) == pytest.approx(1.0)


def test_airflow_factor_penalizes_low_airflow():
    assert airflow_response_factor(
        0.1, **AIRFLOW_TEST_PROFILE
    ) == pytest.approx(0.75)


def test_airflow_factor_penalizes_high_airflow():
    assert airflow_response_factor(
        1.15, **AIRFLOW_TEST_PROFILE
    ) == pytest.approx(0.75)


def test_airflow_factor_reaches_floor_at_stress_limits():
    assert airflow_response_factor(
        0.0, **AIRFLOW_TEST_PROFILE
    ) == pytest.approx(0.5)

    assert airflow_response_factor(
        1.5, **AIRFLOW_TEST_PROFILE
    ) == pytest.approx(0.5)


def test_partial_airflow_parameters_are_rejected():
    with pytest.raises(ValueError):
        airflow_response_factor(
            0.5,
            low_limit_m_s=0.0,
        )
