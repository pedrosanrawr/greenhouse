
"""Air and atmospheric calculations used by GreenLab.

This module initially calculates atmospheric diagnostics. It does not
claim that CO2, VPD, or airflow affects crop growth until the relevant
crop-response parameters have been supplied and integrated.
"""

from dataclasses import dataclass
import math


# Fixed reference used for reproducible scenario comparisons.
# This is a modeling reference, not a greenhouse sensor reading.
DEFAULT_REFERENCE_CO2_PPM = 430.0
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

def _bounded_band_response(
    value: float,
    low_limit: float,
    opt_low: float,
    opt_high: float,
    high_limit: float,
    min_factor: float,
) -> float:
    """Return a bounded response with a flat optimal band."""

    if value <= low_limit or value >= high_limit:
        return min_factor

    if value < opt_low:
        fraction = (
            (value - low_limit) / (opt_low - low_limit)
        )
        return min_factor + (1.0 - min_factor) * fraction

    if value <= opt_high:
        return 1.0

    fraction = (
        (value - opt_high) / (high_limit - opt_high)
    )
    return 1.0 - (1.0 - min_factor) * fraction

def vpd_response_factor(
    vpd_kpa: float,
    low_limit_kpa: float | None = None,
    opt_low_kpa: float | None = None,
    opt_high_kpa: float | None = None,
    high_limit_kpa: float | None = None,
    min_factor: float | None = None,
) -> float:
    """Return a bounded VPD response, or neutral 1.0 if unconfigured."""

    if not math.isfinite(vpd_kpa) or vpd_kpa < 0.0:
        raise ValueError("VPD must be finite and non-negative.")

    parameters = (
        low_limit_kpa,
        opt_low_kpa,
        opt_high_kpa,
        high_limit_kpa,
        min_factor,
    )

    if all(value is None for value in parameters):
        return 1.0

    if any(value is None for value in parameters):
        raise ValueError(
            "All VPD response parameters must be supplied together."
        )

    if not all(math.isfinite(value) for value in parameters):
        raise ValueError("VPD response parameters must be finite.")

    if not (
        0.0 <= low_limit_kpa < opt_low_kpa
        <= opt_high_kpa < high_limit_kpa
    ):
        raise ValueError(
            "VPD limits must satisfy "
            "0 <= low_limit < opt_low <= opt_high < high_limit."
        )

    if not 0.0 <= min_factor <= 1.0:
        raise ValueError("VPD minimum factor must be between 0 and 1.")

    return _bounded_band_response(
        value=vpd_kpa,
        low_limit=low_limit_kpa,
        opt_low=opt_low_kpa,
        opt_high=opt_high_kpa,
        high_limit=high_limit_kpa,
        min_factor=min_factor,
    )

def airflow_response_factor(
    airflow_m_s: float,
    low_limit_m_s: float | None = None,
    opt_low_m_s: float | None = None,
    opt_high_m_s: float | None = None,
    high_limit_m_s: float | None = None,
    min_factor: float | None = None,
) -> float:
    """Return a bounded airflow response, or neutral 1.0 if unconfigured."""

    if not math.isfinite(airflow_m_s) or airflow_m_s < 0.0:
        raise ValueError("Airflow must be finite and non-negative.")

    parameters = (
        low_limit_m_s,
        opt_low_m_s,
        opt_high_m_s,
        high_limit_m_s,
        min_factor,
    )

    if all(value is None for value in parameters):
        return 1.0

    if any(value is None for value in parameters):
        raise ValueError(
            "All airflow response parameters must be supplied together."
        )

    if not all(math.isfinite(value) for value in parameters):
        raise ValueError("Airflow response parameters must be finite.")

    if not (
        0.0 <= low_limit_m_s < opt_low_m_s
        <= opt_high_m_s < high_limit_m_s
    ):
        raise ValueError(
            "Airflow limits must satisfy "
            "0 <= low_limit < opt_low <= opt_high < high_limit."
        )

    if not 0.0 <= min_factor <= 1.0:
        raise ValueError(
            "Airflow minimum factor must be between 0 and 1."
        )

    return _bounded_band_response(
        value=airflow_m_s,
        low_limit=low_limit_m_s,
        opt_low=opt_low_m_s,
        opt_high=opt_high_m_s,
        high_limit=high_limit_m_s,
        min_factor=min_factor,
    )