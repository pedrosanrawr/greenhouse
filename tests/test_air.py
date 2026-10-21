
import pytest

from data.models.air import (
    calculate_air_diagnostics,
    calculate_vpd_kpa,
    co2_response_factor,
)


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
    # At 25 C and 50% RH, VPD is approximately 1.584 kPa.
    assert calculate_vpd_kpa(25.0, 50.0) == pytest.approx(
        1.584, abs=0.002
    )


@pytest.mark.parametrize("rh", [-1.0, 100.1, float("nan")])
def test_invalid_relative_humidity_is_rejected(rh):
    with pytest.raises(ValueError):
        calculate_vpd_kpa(25.0, rh)


def test_co2_response_is_one_at_reference():
    factor = co2_response_factor(
        co2_ppm=426.0,
        k_half_ppm=300.0,
        reference_co2_ppm=426.0,
    )

    assert factor == pytest.approx(1.0)


def test_co2_response_increases_above_reference():
    reference = co2_response_factor(
        co2_ppm=426.0,
        k_half_ppm=300.0,
        reference_co2_ppm=426.0,
    )
    elevated = co2_response_factor(
        co2_ppm=800.0,
        k_half_ppm=300.0,
        reference_co2_ppm=426.0,
    )

    assert elevated > reference


def test_invalid_co2_response_parameter_is_rejected():
    with pytest.raises(ValueError):
        co2_response_factor(
            co2_ppm=426.0,
            k_half_ppm=0.0,
        )


def test_air_diagnostics_calculates_vpd_and_preserves_inputs():
    result = calculate_air_diagnostics(
        temperature_c=25.0,
        co2_ppm=426.0,
        relative_humidity_pct=70.0,
        airflow_m_s=0.5,
    )

    assert result.vpd_kpa == pytest.approx(0.950, abs=0.003)
    assert result.co2_ppm == 426.0
    assert result.relative_humidity_pct == 70.0
    assert result.airflow_m_s == 0.5


def test_negative_airflow_is_rejected():
    with pytest.raises(ValueError):
        calculate_air_diagnostics(
            temperature_c=25.0,
            co2_ppm=426.0,
            relative_humidity_pct=70.0,
            airflow_m_s=-0.1,
        )

from data.models.air import (
    airflow_response_factor,
    vpd_response_factor,
)


def test_vpd_factor_is_neutral_without_crop_parameters():
    assert vpd_response_factor(2.0) == pytest.approx(1.0)


def test_vpd_factor_declines_between_thresholds():
    assert vpd_response_factor(
        1.0, low_kpa=0.5, high_kpa=2.5, min_factor=0.3
    ) == pytest.approx(0.825)


def test_vpd_factor_reaches_minimum():
    assert vpd_response_factor(
        3.0, low_kpa=0.5, high_kpa=2.5, min_factor=0.3
    ) == pytest.approx(0.3)


def test_airflow_factor_is_neutral_without_crop_parameters():
    assert airflow_response_factor(0.8) == pytest.approx(1.0)


def test_airflow_factor_equals_one_at_reference_speed():
    assert airflow_response_factor(
        0.5, sensitivity=0.2, half_saturation_m_s=0.3
    ) == pytest.approx(1.0)


def test_airflow_response_increases_with_airflow():
    low = airflow_response_factor(
        0.1, sensitivity=0.2, half_saturation_m_s=0.3
    )
    high = airflow_response_factor(
        0.8, sensitivity=0.2, half_saturation_m_s=0.3
    )

    assert high > low


def test_partial_vpd_parameters_are_rejected():
    with pytest.raises(ValueError):
        vpd_response_factor(
            1.5, low_kpa=0.5, high_kpa=2.5
        )


def test_partial_airflow_parameters_are_rejected():
    with pytest.raises(ValueError):
        airflow_response_factor(
            0.5, sensitivity=0.2
        )