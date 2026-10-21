from dataclasses import dataclass, field
from datetime import date
from math import isclose
from typing import Dict, Tuple
from math import isclose, isfinite
from data.models.compatibility import validate_crop_requirements

ORGANS = ("leaf", "stem", "root", "flower", "fruit", "root_tuber", "stem_tuber")  # most plants don't have the last 2, so they are 0 in the biomass_ratio


@dataclass(frozen=True)
class CropParameters:
    """Crop-specific param values"""
    name: str
    t_base: float
    t_opt: float
    t_max: float
    lue: float
    extinction_k: float
    sla: float
    maintenance: Dict[str, float]
    sink_demand: Dict[str, float]  # no longer read by the engine; see notes
    # Fraction of new biomass allocated to each organ, per phase (each sums to 1).
    biomass_ratio: Dict[str, Dict[str, float]]
    # NEW: day on which each phase starts, e.g. {"vegetative": 0, "flowering": 35}.
    # Must list the same phases as biomass_ratio, in the same order, strictly ascending.
    phase_start_days: Dict[str, int]
    # NEW: potential total dry biomass of one plant at the end of the cycle (g/plant).
    total_biomass_g: float
    initial_biomass: Dict[str, float]
    harvestable_organ: str
    cycle_min_days: int
    cycle_max_days: int
    first_harvest_min_days: int
    first_harvest_max_days: int
    t_abs_min: float | None = None       
    t_opt_min: float | None = None
    t_opt_max: float | None = None
    t_abs_max: float | None = None
    dli_min: float | None = None         
    dli_opt: float | None = None
    temperature_band_verified: bool = False

    # REMINDER
    # Optional crop-specific atmospheric response parameters.
    # Keep None until suitable values are sourced or calibrated.
    co2_k_half_ppm: float | None = None

    vpd_low_kpa: float | None = None
    vpd_high_kpa: float | None = None
    vpd_min_factor: float | None = None

    airflow_sensitivity: float | None = None
    airflow_half_saturation_m_s: float | None = None

    def __post_init__(self):
        if not self.biomass_ratio:
            raise ValueError(f"{self.name}: biomass_ratio needs at least one phase")

        normalized: Dict[str, Dict[str, float]] = {}
        for phase, ratios in self.biomass_ratio.items():
            unknown = set(ratios) - set(ORGANS)
            if unknown:
                raise ValueError(
                    f"{self.name}/{phase}: unknown organ(s) {sorted(unknown)}; "
                    f"allowed: {ORGANS}"
                )
            bad = {o: v for o, v in ratios.items() if not 0.0 <= v <= 1.0}
            if bad:
                raise ValueError(f"{self.name}/{phase}: ratios must be in [0, 1], got {bad}")
            total = sum(ratios.values())
            if not isclose(total, 1.0, abs_tol=1e-6):
                raise ValueError(f"{self.name}/{phase}: ratios sum to {total:.4f}, expected 1.0")
            normalized[phase] = {o: float(ratios.get(o, 0.0)) for o in ORGANS}
        object.__setattr__(self, "biomass_ratio", normalized)

        # ---- phase thresholds
        if set(self.phase_start_days) != set(normalized):
            raise ValueError(
                f"{self.name}: phase_start_days phases {sorted(self.phase_start_days)} "
                f"must match biomass_ratio phases {sorted(normalized)}"
            )
        starts = [self.phase_start_days[p] for p in normalized]  # biomass_ratio order
        if starts[0] != 0:
            raise ValueError(f"{self.name}: first phase must start on day 0, got {starts[0]}")
        if any(b <= a for a, b in zip(starts, starts[1:])):
            raise ValueError(
                f"{self.name}: phase_start_days must be strictly ascending in the same "
                f"order as biomass_ratio, got {dict(zip(normalized, starts))}"
            )
        if starts[-1] >= self.cycle_max_days:
            raise ValueError(
                f"{self.name}: last phase starts on day {starts[-1]}, "
                f"which is not before cycle_max_days={self.cycle_max_days}"
            )

        # ---- total biomass
        if self.total_biomass_g <= sum(self.initial_biomass.values()):
            raise ValueError(f"{self.name}: total_biomass_g must exceed initial biomass")

        # ---- Optional CO2 response parameter
        if self.co2_k_half_ppm is not None:
            if (
                not isfinite(self.co2_k_half_ppm)
                or self.co2_k_half_ppm <= 0.0
            ):
                raise ValueError(
                    f"{self.name}: co2_k_half_ppm must be finite and positive"
                )

        # ---- Optional VPD response parameters
        vpd_parameters = (
            self.vpd_low_kpa,
            self.vpd_high_kpa,
            self.vpd_min_factor,
        )

        if any(v is not None for v in vpd_parameters):
            if not all(v is not None for v in vpd_parameters):
                raise ValueError(
                    f"{self.name}: all VPD response parameters must be supplied together"
                )

            low, high, minimum = vpd_parameters

            if not all(isfinite(v) for v in vpd_parameters):
                raise ValueError(
                    f"{self.name}: VPD parameters must be finite"
                )

            if low < 0.0 or high <= low:
                raise ValueError(
                    f"{self.name}: VPD limits must satisfy 0 <= low < high"
                )

            if not 0.0 <= minimum <= 1.0:
                raise ValueError(
                    f"{self.name}: VPD minimum factor must be between 0 and 1"
                )

        # ---- Optional airflow response parameters
        airflow_parameters = (
            self.airflow_sensitivity,
            self.airflow_half_saturation_m_s,
        )

        if any(v is not None for v in airflow_parameters):
            if not all(v is not None for v in airflow_parameters):
                raise ValueError(
                    f"{self.name}: both airflow parameters must be supplied together"
                )

            sensitivity, half_saturation = airflow_parameters

            if (
                not isfinite(sensitivity)
                or not isfinite(half_saturation)
                or sensitivity < 0.0
                or half_saturation <= 0.0
            ):
                raise ValueError(
                    f"{self.name}: invalid airflow response parameters"
                )

        validate_crop_requirements(
            t_abs_min=self.t_abs_min,
            t_opt_min=self.t_opt_min,
            t_opt_max=self.t_opt_max,
            t_abs_max=self.t_abs_max,
            dli_min=self.dli_min,
            dli_opt=self.dli_opt,
            temperature_band_verified=self.temperature_band_verified,
        )

    @property
    def phases(self) -> Tuple[str, ...]:
        return tuple(self.biomass_ratio)

    def ratio_for(self, phase: str) -> Dict[str, float]:
        try:
            return self.biomass_ratio[phase]
        except KeyError:
            raise KeyError(
                f"{self.name} has no biomass_ratio for phase '{phase}'. "
                f"Defined phases: {self.phases}"
            ) from None

    def phase_for_day(self, day: int) -> str:
        """Phase active on a given day (0-based): the last phase whose start <= day."""
        if day < 0:
            raise ValueError("day must be >= 0")
        current = self.phases[0]
        for phase in self.phases:
            if day >= self.phase_start_days[phase]:
                current = phase
        return current

    @property
    def growth_days(self) -> int:
        """Days over which total_biomass_g is accumulated."""
        return self.cycle_max_days

    @property
    def potential_daily_growth_g(self) -> float:
        """Flat daily biomass potential for one plant (g/day). Gradient can replace this later."""
        return (self.total_biomass_g - sum(self.initial_biomass.values())) / self.growth_days

@dataclass(frozen=True)
class GreenhouseConfig:
    temperature_c: float
    light_hours: float
    irradiance_ppfd: float
    airflow_m_s: float
    area_per_plant_m2: float = 0.25
    water_factor: float = 1.0
    nutrient_factor: float = 1.0
    start_date: date | None = None
    cover_par_transmittance: float = 0.86
    co2_ppm: float = 426.0
    relative_humidity_pct: float = 70.0    

@dataclass(frozen=True)
class EnvironmentConditions:
    temperature_c: float
    light_hours: float
    irradiance_ppfd: float
    airflow_m_s: float

    # Daily weather and greenhouse-cover data for the light model.
    solar_radiation_mj_m2_day: float
    cover_par_transmittance: float

    co2_ppm: float = 426.0
    relative_humidity_pct: float = 70.0    

@dataclass(frozen=True)
class ResourceAvailability:
    water_factor: float = 1.0
    nutrient_factor: float = 1.0


@dataclass
class CropState:
    biomass_g: Dict[str, float]
    reserve_g: float = 0.0
    senesced_biomass_g: float = 0.0
    development_day: int = 0


@dataclass
class GrowthFlux:
    """Calculated changes for one time step; the engine applies these to CropState."""
    organ_growth_g: Dict[str, float]
    organ_loss_g: Dict[str, float]
    reserve_after_g: float
    lai: float
    gross_assimilation_g_day: float
    maintenance_respiration_g_day: float
    sink_demand_g_day: float
    limiting_factor: str
    temperature_factor: float
    environment_factor: float
    maintenance_deficit_g_day: float = 0.0

    # Atmospheric diagnostics and response factors
    vpd_kpa: float = 0.0

    co2_factor: float = 1.0
    vpd_factor: float = 1.0
    airflow_factor: float = 1.0

    co2_response_active: bool = False
    vpd_response_active: bool = False
    airflow_response_active: bool = False


@dataclass(frozen=True)
class YieldState:
    """Yield estimate; this baseline does not remove harvested biomass from the plant."""
    harvestable_biomass_g: float
    yield_ready: bool