"""Daily light interception calculations for the greenhouse model."""

from dataclasses import dataclass
import math


DEFAULT_PAR_FRACTION = 0.45

# ASSUMPTION: approximate conversion for sunlight, in mol of photons per MJ of
# PAR energy. Used only to report the daily light integral (DLI).
PAR_MOL_PER_MJ = 4.6


@dataclass(frozen=True)
class LightResult:
    outside_solar_mj_m2_day: float
    outside_par_mj_m2_day: float
    inside_par_mj_m2_day: float
    lai: float
    intercepted_fraction: float
    ipar_mj_m2_day: float

    @property
    def dli_mol_par_m2_day(self) -> float:
        """Daily light integral inside the cover, before canopy interception.

        Identical for every crop in a run, because it ignores the canopy.
        """
        return self.inside_par_mj_m2_day * PAR_MOL_PER_MJ


def calculate_light(
    solar_radiation_mj_m2_day: float,
    leaf_biomass_g: float,
    sla_m2_g: float,
    extinction_k: float,
    area_per_plant_m2: float,
    cover_par_transmittance: float,
    par_fraction: float = DEFAULT_PAR_FRACTION,
) -> LightResult:
    """Calculate daily PAR interception for a crop canopy.

    IPAR is reported per square metre of ground area.
    This function does not calculate biomass growth.
    """
    values = (
        solar_radiation_mj_m2_day,
        leaf_biomass_g,
        sla_m2_g,
        extinction_k,
        area_per_plant_m2,
        cover_par_transmittance,
        par_fraction,
    )

    if not all(math.isfinite(v) for v in values):
        raise ValueError("Light parameters must be finite.")

    if solar_radiation_mj_m2_day < 0:
        raise ValueError("Solar radiation cannot be negative.")
    if leaf_biomass_g < 0 or sla_m2_g < 0 or extinction_k < 0:
        raise ValueError("Leaf biomass, SLA, and extinction_k cannot be negative.")
    if area_per_plant_m2 <= 0:
        raise ValueError("Area per plant must be greater than zero.")
    if not 0 <= cover_par_transmittance <= 1:
        raise ValueError("Cover PAR transmittance must be between 0 and 1.")
    if not 0 <= par_fraction <= 1:
        raise ValueError("PAR fraction must be between 0 and 1.")

    outside_par = solar_radiation_mj_m2_day * par_fraction
    inside_par = outside_par * cover_par_transmittance

    leaf_area_m2 = leaf_biomass_g * sla_m2_g
    lai = leaf_area_m2 / area_per_plant_m2

    intercepted_fraction = -math.expm1(-extinction_k * lai)
    ipar = inside_par * intercepted_fraction

    return LightResult(
        outside_solar_mj_m2_day=solar_radiation_mj_m2_day,
        outside_par_mj_m2_day=outside_par,
        inside_par_mj_m2_day=inside_par,
        lai=lai,
        intercepted_fraction=intercepted_fraction,
        ipar_mj_m2_day=ipar,
    )

def calculate_dli(
    solar_radiation_mj_m2_day: float,
    cover_par_transmittance: float,
    par_fraction: float = DEFAULT_PAR_FRACTION,
) -> tuple[float, float]:
    """Return (inside_par_mj_m2_day, dli_mol_par_m2_day) before canopy interception."""
    values = (solar_radiation_mj_m2_day, cover_par_transmittance, par_fraction)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Light parameters must be finite.")
    if solar_radiation_mj_m2_day < 0:
        raise ValueError("Solar radiation cannot be negative.")
    if not 0 <= cover_par_transmittance <= 1:
        raise ValueError("Cover PAR transmittance must be between 0 and 1.")
    if not 0 <= par_fraction <= 1:
        raise ValueError("PAR fraction must be between 0 and 1.")

    inside_par = solar_radiation_mj_m2_day * par_fraction * cover_par_transmittance
    return inside_par, inside_par * PAR_MOL_PER_MJ