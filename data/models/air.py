
"""Air and atmospheric calculations used by GreenLab.

This module initially calculates atmospheric diagnostics. It does not
claim that CO2, VPD, or airflow affects crop growth until the relevant
crop-response parameters have been supplied and integrated.
"""

from dataclasses import dataclass
import math


# Fixed reference used for reproducible scenario comparisons.
# This is a modeling reference, not a greenhouse sensor reading.
DEFAULT_REFERENCE_CO2_PPM = 426.0
DEFAULT_REFERENCE_AIRFLOW_M_S = 0.5

@dataclass(frozen=True)
class AirDiagnostics:
    """Atmospheric inputs and calculated VPD for one simulation day."""

    co2_ppm: float
    relative_humidity_pct: float
    airflow_m_s: float
    vpd_kpa: float


def calculate_vpd_kpa(
    temperature_c: float,
    relative_humidity_pct: float,
) -> float:
    """Calculate VPD from air temperature and relative humidity."""

    if not math.isfinite(temperature_c):
        raise ValueError("Temperature must be finite.")

    if not math.isfinite(relative_humidity_pct):
        raise ValueError("Relative humidity must be finite.")

    if temperature_c <= -237.3:
        raise ValueError("Temperature is outside the valid equation domain.")

    if not 0.0 <= relative_humidity_pct <= 100.0:
        raise ValueError("Relative humidity must be between 0 and 100%.")

    saturation_vapor_pressure = 0.6108 * math.exp(
        (17.27 * temperature_c) / (temperature_c + 237.3)
    )

    vpd = saturation_vapor_pressure * (
        1.0 - relative_humidity_pct / 100.0
    )

    return max(0.0, vpd)


def co2_response_factor(
    co2_ppm: float,
    k_half_ppm: float,
    reference_co2_ppm: float = DEFAULT_REFERENCE_CO2_PPM,
) -> float:
    """Return a normalized empirical CO2-response factor.

    The caller must provide a suitable crop-specific half-saturation
    parameter. This function does not assign that parameter.

    A factor of 1 means the configured CO2 concentration equals the
    reference concentration under this model.
    """

    values = (co2_ppm, k_half_ppm, reference_co2_ppm)

    if not all(math.isfinite(value) for value in values):
        raise ValueError("CO2 response parameters must be finite.")

    if co2_ppm < 0.0:
        raise ValueError("CO2 concentration cannot be negative.")

    if k_half_ppm <= 0.0:
        raise ValueError("The CO2 half-saturation parameter must be positive.")

    if reference_co2_ppm <= 0.0:
        raise ValueError("Reference CO2 concentration must be positive.")

    response = co2_ppm / (co2_ppm + k_half_ppm)
    reference_response = (
        reference_co2_ppm / (reference_co2_ppm + k_half_ppm)
    )

    return response / reference_response


def calculate_air_diagnostics(
    temperature_c: float,
    co2_ppm: float,
    relative_humidity_pct: float,
    airflow_m_s: float,
) -> AirDiagnostics:
    """Validate atmospheric inputs and calculate VPD."""

    if not math.isfinite(co2_ppm) or co2_ppm < 0.0:
        raise ValueError("CO2 concentration must be finite and non-negative.")

    if not math.isfinite(airflow_m_s) or airflow_m_s < 0.0:
        raise ValueError("Airflow must be finite and non-negative.")

    vpd_kpa = calculate_vpd_kpa(
        temperature_c=temperature_c,
        relative_humidity_pct=relative_humidity_pct,
    )

    return AirDiagnostics(
        co2_ppm=co2_ppm,
        relative_humidity_pct=relative_humidity_pct,
        airflow_m_s=airflow_m_s,
        vpd_kpa=vpd_kpa,
    )

def vpd_response_factor(
    vpd_kpa: float,
    low_kpa: float | None = None,
    high_kpa: float | None = None,
    min_factor: float | None = None,
) -> float:
    """Return a crop-specific VPD factor, or neutral 1.0 if unconfigured."""

    if not math.isfinite(vpd_kpa) or vpd_kpa < 0.0:
        raise ValueError("VPD must be finite and non-negative.")

    parameters = (low_kpa, high_kpa, min_factor)

    if all(value is None for value in parameters):
        return 1.0

    if any(value is None for value in parameters):
        raise ValueError("All VPD response parameters must be supplied together.")

    if not all(math.isfinite(value) for value in parameters):
        raise ValueError("VPD response parameters must be finite.")

    if low_kpa < 0.0 or high_kpa <= low_kpa:
        raise ValueError("VPD limits must satisfy 0 <= low < high.")

    if not 0.0 <= min_factor <= 1.0:
        raise ValueError("Minimum VPD factor must be between 0 and 1.")

    if vpd_kpa <= low_kpa:
        return 1.0

    if vpd_kpa >= high_kpa:
        return min_factor

    fraction = (vpd_kpa - low_kpa) / (high_kpa - low_kpa)

    return 1.0 - (1.0 - min_factor) * fraction


def airflow_response_factor(
    airflow_m_s: float,
    sensitivity: float | None = None,
    half_saturation_m_s: float | None = None,
    reference_m_s: float = DEFAULT_REFERENCE_AIRFLOW_M_S,
) -> float:
    """Optional empirical airflow response normalized at reference airflow.

    Returns neutral 1.0 when crop-specific parameters are unavailable.
    """

    if not math.isfinite(airflow_m_s) or airflow_m_s < 0.0:
        raise ValueError("Airflow must be finite and non-negative.")

    if not math.isfinite(reference_m_s) or reference_m_s <= 0.0:
        raise ValueError("Reference airflow must be finite and positive.")

    if sensitivity is None and half_saturation_m_s is None:
        return 1.0

    if sensitivity is None or half_saturation_m_s is None:
        raise ValueError("Both airflow response parameters must be supplied.")

    if (
        not math.isfinite(sensitivity)
        or not math.isfinite(half_saturation_m_s)
        or sensitivity < 0.0
        or half_saturation_m_s <= 0.0
    ):
        raise ValueError("Invalid airflow response parameters.")

    def raw_response(speed: float) -> float:
        return 1.0 + sensitivity * (
            speed / (speed + half_saturation_m_s)
        )

    return raw_response(airflow_m_s) / raw_response(reference_m_s)