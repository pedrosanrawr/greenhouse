"""Texture-based soil water and fertilizer model.

Replaces the pass-through ``GenericSoilFertilizerModel``. One file, five parts:

    SoilProfile          texture + hydraulics (stateless data)
    WaterBalance         root-zone water; returns a WaterFlux each day
    NutrientPools        N, P2O5, K2O pools; consume the WaterFlux
    DemandLedger         per-crop daily demand shared by water and nutrients
    TextureSoilFertilizerModel   facade: the day clock and the call order

Public entry point: ``TextureSoilFertilizerModel`` (same constructor as before,
plus an optional ``tracked_nutrients`` argument).
Everything marked ASSUMPTION is a placeholder, not a sourced value.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Iterable, Mapping

from data.models.contracts import SoilFertilizerModel
from data.models.types import CropParameters, GreenhouseConfig, ResourceAvailability

# --------------------------------------------------------------------------- #
# Helpers

# --------------------------------------------------------------------------- #
def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

# --------------------------------------------------------------------------- #
# SoilProfile: texture presets and Saxton & Rawls (2006) hydraulics
# Soil texture presets, Saxton & Rawls (2006) pedotransfer functions, and ``SoilProfile``.
#
# Everything in this module is stateless. It answers one question: what are the
# hydraulic properties of this soil? Water and nutrient state live elsewhere.
#
# Everything marked ASSUMPTION is a placeholder, not a sourced value.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SoilTexture:
    """Soil texture. ``sand`` and ``clay`` are fractions (0-1), OM is in percent."""

    name: str
    sand: float
    clay: float
    organic_matter_pct: float = 2.5
    # Alternative class-average values (wilting point, field capacity, saturation)
    # from the last three columns of the project soil table, in m3/m3.
    class_average: tuple[float, float, float] | None = None
    reference_soils: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.sand <= 1.0 and 0.0 <= self.clay <= 1.0):
            raise ValueError("sand and clay must be fractions between 0 and 1")
        if self.sand + self.clay > 1.0 + 1e-9:
            raise ValueError("sand + clay must not exceed 1")
        if self.organic_matter_pct < 0.0:
            raise ValueError("organic matter must be non-negative")

SOIL_TEXTURES: dict[str, SoilTexture] = {
    "clay": SoilTexture(
        "Clay", 0.20, 0.60, 2.5, (0.272, 0.396, 0.475),
        "Faraon, Bantog (clay, Capiz); Bigaa, Candaba (clayey, Bulacan/Pampanga)",
        "Assumption: sand/clay set near the USDA class center; OM 2.5% assumed for all. Adjustable.",
    ),
    "clay_loam": SoilTexture(
        "Clay loam", 0.32, 0.34, 2.5, (0.197, 0.318, 0.464),
        "Luisiana, San Manuel, Alimodian (Capiz); Bantog clay loam (Nueva Ecija)",
        "Assumption: same as above.",
    ),
    "loam": SoilTexture(
        "Loam", 0.40, 0.20, 2.5, (0.117, 0.270, 0.463),
        "Maligaya loam (Nueva Ecija)",
        "Assumption: same as above.",
    ),
    "sandy_loam": SoilTexture(
        "Sandy loam", 0.65, 0.10, 2.5, (0.095, 0.207, 0.453),
        "Quingua (sandy loam surface), Obando (sandy loam), both Bulacan",
        "Assumption: same as above.",
    ),
}

def get_texture(soil: str | SoilTexture) -> SoilTexture:
    """Return a preset by name ('Clay loam', 'clay-loam', 'clay_loam') or pass a texture through."""
    if isinstance(soil, SoilTexture):
        return soil
    key = soil.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in SOIL_TEXTURES:
        raise ValueError(f"Unknown soil '{soil}'. Presets: {', '.join(SOIL_TEXTURES)}")
    return SOIL_TEXTURES[key]

@dataclass(frozen=True)
class SoilHydraulics:
    wilting_point: float  # m3/m3 at -1500 kPa
    field_capacity: float  # m3/m3 at -33 kPa
    saturation: float  # m3/m3
    plant_available_water: float  # field capacity - wilting point, m3/m3
    b: float  # moisture-tension slope
    lambda_: float  # 1 / b
    ksat_mm_h: float  # saturated hydraulic conductivity, mm/h
    bulk_density: float  # g/cm3

def saxton_rawls_hydraulics(sand: float, clay: float, organic_matter_pct: float) -> SoilHydraulics:
    """Soil water properties from sand and clay (fractions) and organic matter (%).

    Saxton & Rawls (2006) give the equations for clay <= 60% and OM <= 8%.
    """
    s, c, om = sand, clay, organic_matter_pct
    if c > 0.60 or om > 8.0:
        warnings.warn("Texture is outside the Saxton & Rawls (2006) range (clay <= 60%, OM <= 8%).")

    wp_t = -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * s * om - 0.013 * c * om + 0.068 * s * c + 0.031
    wp = wp_t + (0.14 * wp_t - 0.02)
    fc_t = -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * s * om - 0.027 * c * om + 0.452 * s * c + 0.299
    fc = fc_t + (1.283 * fc_t**2 - 0.374 * fc_t - 0.015)
    sat_t = 0.278 * s + 0.034 * c + 0.022 * om - 0.018 * s * om - 0.027 * c * om - 0.584 * s * c + 0.078
    sat_minus_fc = sat_t + (0.636 * sat_t - 0.107)
    sat = fc + sat_minus_fc - 0.097 * s + 0.043

    bulk_density = (1.0 - sat) * 2.65
    b = (math.log(1500.0) - math.log(33.0)) / (math.log(fc) - math.log(wp))
    lam = 1.0 / b
    ksat = 1930.0 * (sat - fc) ** (3.0 - lam)
    return SoilHydraulics(wp, fc, sat, fc - wp, b, lam, ksat, bulk_density)

@dataclass(frozen=True)
class SoilProfile:
    """A soil texture together with its hydraulic properties. Plain data, no state.

    Both ``WaterBalance`` and any future nutrient process that needs soil
    properties (P fixation by clay, CEC, OM mineralization) read from this.
    """

    texture: SoilTexture
    hydraulics: SoilHydraulics

    @classmethod
    def build(cls, soil: str | SoilTexture = "loam", hydraulic_source: str = "saxton_rawls") -> "SoilProfile":
        if hydraulic_source not in ("saxton_rawls", "class_average"):
            raise ValueError("hydraulic_source must be 'saxton_rawls' or 'class_average'")
        texture = get_texture(soil)
        h = saxton_rawls_hydraulics(texture.sand, texture.clay, texture.organic_matter_pct)
        if hydraulic_source == "class_average":
            if texture.class_average is None:
                raise ValueError("this soil has no class-average values")
            wp, fc, sat = texture.class_average
            if not wp < fc < sat:
                raise ValueError("class-average values must satisfy wilting point < field capacity < saturation")
            h = SoilHydraulics(wp, fc, sat, fc - wp, h.b, h.lambda_, h.ksat_mm_h, h.bulk_density)
        return cls(texture, h)

# --------------------------------------------------------------------------- #
# WaterBalance: root-zone water, hands a WaterFlux to the nutrients
# Root-zone water balance. Knows nothing about nutrients or crops.
#
# Water (mm, root zone):
#   * Available water (AW) lies between wilting point and field capacity.
#   * Water above field capacity is gravitational water; it drains each day at up
#     to Ksat x 24 mm. Anything beyond saturation runs off.
#   * factor = AW / ((1 - p) x TAW), limited to 0-1, where TAW is the total
#     available water and p is ``depletion_fraction``. With p = 0 this is
#     AW / TAW, the same linear form as the project's normalized water factor.
#
# The only thing this class hands to other components is a ``WaterFlux`` value.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class IrrigationSchedule:
    """ASSUMPTION: 12 mm every 3 days is a placeholder, roughly matching the default demand."""

    interval_days: int = 3
    amount_mm: float = 12.0
    start_day: int = 0

    def __post_init__(self) -> None:
        if self.interval_days < 1 or self.amount_mm < 0.0 or self.start_day < 0:
            raise ValueError("invalid irrigation schedule")

    def event_on(self, day: int) -> bool:
        return day >= self.start_day and (day - self.start_day) % self.interval_days == 0

@dataclass(frozen=True)
class WaterFlux:
    """What the water balance did on one day. Passed by value to the nutrient pools."""

    uptake_mm: float
    drained_mm: float
    field_capacity_mm: float  # root-zone water held at field capacity (mixing volume)

    @property
    def washout_fraction(self) -> float:
        """Share of a fully mobile pool carried away by this day's drainage."""
        if self.field_capacity_mm <= 0.0:
            return 0.0
        return 1.0 - math.exp(-self.drained_mm / self.field_capacity_mm)

class WaterBalance:
    def __init__(
        self,
        profile: SoilProfile,
        irrigation: IrrigationSchedule | None = None,
        *,
        root_zone_depth_m: float = 0.30,  # ASSUMPTION
        depletion_fraction: float = 0.0,
        initial_water_fraction: float = 1.0,  # share of TAW at the start
    ) -> None:
        if root_zone_depth_m <= 0.0:
            raise ValueError("root zone depth must be positive")
        if not 0.0 <= depletion_fraction < 1.0:
            raise ValueError("depletion_fraction must be in [0, 1)")
        self.profile = profile
        self.irrigation = irrigation or IrrigationSchedule()
        self.root_zone_depth_m = root_zone_depth_m
        self.depletion_fraction = depletion_fraction
        self.initial_water_fraction = clamp01(initial_water_fraction)

        h = profile.hydraulics
        depth_mm = root_zone_depth_m * 1000.0
        self.taw_mm = h.plant_available_water * depth_mm
        self.gravitational_capacity_mm = (h.saturation - h.field_capacity) * depth_mm
        self.field_capacity_mm = h.field_capacity * depth_mm
        self.reset()

    # -- state ------------------------------------------------------------- #
    def reset(self) -> None:
        self._aw_mm = self.initial_water_fraction * self.taw_mm
        self._grav_mm = 0.0
        self._cum = {"irrigation_mm": 0.0, "water_uptake_mm": 0.0, "drained_mm": 0.0, "runoff_mm": 0.0}

    @property
    def available_water_mm(self) -> float:
        return self._aw_mm

    @property
    def gravitational_mm(self) -> float:
        return self._grav_mm

    def cumulative(self) -> dict[str, float]:
        return dict(self._cum)

    # -- daily steps ------------------------------------------------------- #
    def open_day(self, day: int) -> None:
        if self.irrigation.event_on(day):
            self._add_water(self.irrigation.amount_mm)

    def close_day(self, demand_mm: float) -> WaterFlux:
        uptake = min(demand_mm, self._aw_mm)
        self._aw_mm -= uptake
        self._cum["water_uptake_mm"] += uptake

        drained = min(self._grav_mm, self.profile.hydraulics.ksat_mm_h * 24.0)
        self._grav_mm -= drained
        self._cum["drained_mm"] += drained
        return WaterFlux(uptake, drained, self.field_capacity_mm)

    def factor(self, demand_mm: float | None = None) -> float:
        if self.taw_mm <= 0.0:
            return 0.0
        if demand_mm is not None:
            if demand_mm <= 0.0:
                return 1.0
            return clamp01(self._aw_mm / demand_mm)
        return clamp01(self._aw_mm / ((1.0 - self.depletion_fraction) * self.taw_mm))

    def _add_water(self, mm: float) -> None:
        self._cum["irrigation_mm"] += mm
        to_aw = min(mm, self.taw_mm - self._aw_mm)
        self._aw_mm += to_aw
        remaining = mm - to_aw
        to_grav = min(remaining, self.gravitational_capacity_mm - self._grav_mm)
        self._grav_mm += to_grav
        self._cum["runoff_mm"] += remaining - to_grav

# --------------------------------------------------------------------------- #
# NutrientPools: N, P2O5, K2O pools
# N, P2O5 and K2O pools (kg/ha). Knows nothing about soil texture or water state.
#
#   * The pools start from the indigenous supply and receive the applied fertilizer.
#   * Uptake is limited to the pool.
#   * Drainage carries away part of each pool (ASSUMPTION: simple mixing with the
#     water held at field capacity, scaled by ``leaching_mobility``; only N is
#     mobile by default). The drainage arrives as a ``WaterFlux`` value.
#   * factor = min (or product) over the tracked nutrients of min(1, pool / demand),
#     where the demand is the previous day's total, so every crop sees the same
#     factor on a given day.
#   * ``tracked`` chooses which nutrients are modelled. A nutrient that is not
#     tracked has no pool and never limits growth (it is treated as non-limiting).
#     With no tracked nutrients the factor is always 1.
# --------------------------------------------------------------------------- #
NUTRIENTS = ("n", "p2o5", "k2o")

@dataclass(frozen=True)
class NutrientApplication:
    """Fertilizer applied per hectare (project inputs M8-M10).

    ``schedule`` lists (day, fraction) pairs; fractions must sum to 1.
    ASSUMPTION: by default everything is applied on day 0 ("user adjusts at start").
    """

    n_kg_ha: float = 0.0  # N_app, kg N/ha
    p2o5_kg_ha: float = 0.0  # P_app, kg P2O5/ha
    k2o_kg_ha: float = 0.0  # K_app, kg K2O/ha
    schedule: tuple[tuple[int, float], ...] = ((0, 1.0),)

    def __post_init__(self) -> None:
        if min(self.n_kg_ha, self.p2o5_kg_ha, self.k2o_kg_ha) < 0.0:
            raise ValueError("applied nutrient amounts must be non-negative")
        if not self.schedule or any(d < 0 or f < 0 for d, f in self.schedule):
            raise ValueError("schedule needs non-negative days and fractions")
        if abs(sum(f for _, f in self.schedule) - 1.0) > 1e-9:
            raise ValueError("schedule fractions must sum to 1")

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.n_kg_ha, self.p2o5_kg_ha, self.k2o_kg_ha)

class NutrientPools:
    def __init__(
        self,
        application: NutrientApplication,
        indigenous_npk_kg_ha: tuple[float, float, float] = (0.0, 0.0, 0.0),
        leaching_mobility: Mapping[str, float] | None = None,  # ASSUMPTION
        combination: str = "min",
        tracked: Iterable[str] = NUTRIENTS,
    ) -> None:
        if combination not in ("min", "product"):
            raise ValueError("nutrient_combination must be 'min' or 'product'")
        tracked = tuple(tracked)
        unknown = [k for k in tracked if k not in NUTRIENTS]
        if unknown:
            raise ValueError(f"unknown nutrient(s) {unknown}; choose from {NUTRIENTS}")
        self.application = application
        self.indigenous_npk_kg_ha = tuple(indigenous_npk_kg_ha)
        self.combination = combination
        self.tracked = tuple(k for k in NUTRIENTS if k in tracked)  # canonical order, no duplicates
        self.leaching_mobility = {"n": 1.0, "p2o5": 0.0, "k2o": 0.0}
        if leaching_mobility:
            self.leaching_mobility.update({k: clamp01(v) for k, v in leaching_mobility.items()})
        self.reset()

    # -- state ------------------------------------------------------------- #
    def reset(self) -> None:
        self._pools = {k: float(v) for k, v in zip(NUTRIENTS, self.indigenous_npk_kg_ha)}
        self._prev_demand = (0.0, 0.0, 0.0)
        self._days_closed = 0
        self._cum = {f"{k}_{what}": 0.0 for what in ("applied", "uptake", "leached") for k in NUTRIENTS}

    def levels(self) -> dict[str, float]:
        return dict(self._pools)

    def cumulative(self) -> dict[str, float]:
        return dict(self._cum)

    # -- daily steps ------------------------------------------------------- #
    def open_day(self, day: int) -> None:
        applied = self.application.as_tuple()
        for event_day, fraction in self.application.schedule:
            if event_day == day:
                for key, amount in zip(NUTRIENTS, applied):
                    if key not in self.tracked:
                        continue
                    self._pools[key] += fraction * amount
                    self._cum[f"{key}_applied"] += fraction * amount

    def close_day(self, demand_npk: tuple[float, float, float], flux: WaterFlux) -> None:
        washout = flux.washout_fraction
        for i, key in enumerate(NUTRIENTS):
            if key not in self.tracked:
                continue
            uptake = min(demand_npk[i], self._pools[key])
            self._pools[key] -= uptake
            self._cum[f"{key}_uptake"] += uptake
            leached = self._pools[key] * washout * self.leaching_mobility[key]
            self._pools[key] -= leached
            self._cum[f"{key}_leached"] += leached
        self._prev_demand = tuple(demand_npk)
        self._days_closed += 1

    def factor(self) -> float:
        parts: list[float] = []
        demand_known = self._days_closed >= 1  # the first day has no previous-day demand yet
        for i, key in enumerate(NUTRIENTS):
            if key not in self.tracked:
                continue
            pool, demand = self._pools[key], self._prev_demand[i]
            if not demand_known:
                parts.append(1.0 if pool > 0.0 else 0.0)
            elif demand <= 0.0:
                parts.append(1.0)
            elif pool <= 0.0:
                parts.append(0.0)
            else:
                parts.append(min(1.0, pool / demand))
        if not parts:  # no tracked nutrients: nothing limits growth
            return 1.0
        if self.combination == "product":
            return math.prod(parts)
        return min(parts)

# --------------------------------------------------------------------------- #
# DemandLedger: per-crop daily demand shared by water and nutrients
# Per-day crop demand ledger. Shared by water and nutrients, owned by neither.
#
# Each crop registers once per day; the ledger turns its coefficients into a
# fallback water demand (mm) and N-P2O5-K2O demand (kg/ha). The engine can
# overwrite those with its own figures through ``record_uptake``. At the end of
# the day the ledger hands the totals to the facade and clears itself.
# --------------------------------------------------------------------------- #
# ASSUMPTION: placeholder recommended rates in kg/ha, used only when a crop has no
# entry in ``recommended_npk``. They are NOT recommendations; replace them with the
# crop-specific DA-BPI / PhilRice rates (Step 2). The fallback is scaled by the
# crop's nutrient demand coefficient.
DEFAULT_RECOMMENDED_NPK = (100.0, 60.0, 60.0)

# Attribute names read from the crop object. Edit these if the CropParameters
# fields are named differently.
ATTR_CROP_NAME = "name"
ATTR_WATER_COEFF = "water_demand_coefficient"
ATTR_NUTRIENT_COEFF = "nutrient_demand_coefficient"
ATTR_AREA_FRACTION = "area_fraction"  # optional; share of the growing area, default 1.0
ATTR_SEASON_DAYS = "growth_days"  # CropParameters.growth_days; days the engine spends growing the crop

@dataclass(frozen=True)
class DayDemand:
    water_mm: float
    npk_kg_ha: tuple[float, float, float]

class DemandLedger:
    def __init__(
        self,
        reference_demand_mm_day: float = 4.0,  # ASSUMPTION
        season_days: int = 90,  # fallback, used only when the crop has no growth_days
        recommended_npk: Mapping[str, tuple[float, float, float]] | None = None,
    ) -> None:
        if season_days < 1 or reference_demand_mm_day < 0.0:
            raise ValueError("season days must be at least 1 and reference demand must not be negative")
        self.reference_demand_mm_day = reference_demand_mm_day
        self.season_days = season_days
        self._recommended = {k.strip().lower(): tuple(v) for k, v in (recommended_npk or {}).items()}
        self._warned: set[str] = set()
        self.reset()

    def reset(self) -> None:
        self._registered: dict[str, DayDemand] = {}

    def register(self, crop) -> None:
        name = str(getattr(crop, ATTR_CROP_NAME, id(crop)))
        key = name.strip().lower()
        weight = clamp01(getattr(crop, ATTR_AREA_FRACTION, 1.0))
        season_days = getattr(crop, ATTR_SEASON_DAYS, None)
        season_days = int(season_days) if season_days and season_days >= 1 else self.season_days
        water_coeff = float(getattr(crop, ATTR_WATER_COEFF, 1.0))
        nutrient_coeff = float(getattr(crop, ATTR_NUTRIENT_COEFF, 1.0))
        rates = self._recommended.get(key)
        if rates is None:
            if key not in self._warned:
                self._warned.add(key)
                # stacklevel=3 points at the caller of resources_for_day
                warnings.warn(
                    f"No recommended N-P2O5-K2O rates for '{name}'; using placeholder "
                    f"{DEFAULT_RECOMMENDED_NPK} scaled by its nutrient demand coefficient.",
                    stacklevel=3,
                )
            rates = tuple(r * nutrient_coeff for r in DEFAULT_RECOMMENDED_NPK)
        # Registering again on the same day keeps the first entry (and any recorded uptake).
        if key not in self._registered:
            self._registered[key] = DayDemand(
                water_mm=self.reference_demand_mm_day * water_coeff * weight,
                npk_kg_ha=tuple(weight * r / season_days for r in rates),
            )

    def record_uptake(
        self,
        crop_name: str,
        water_mm: float | None = None,
        n_kg_ha: float | None = None,
        p2o5_kg_ha: float | None = None,
        k2o_kg_ha: float | None = None,
    ) -> None:
        key = crop_name.strip().lower()
        if key not in self._registered:
            raise KeyError(f"crop '{crop_name}' has not requested resources on the current day")
        old = self._registered[key]
        npk = tuple(new if new is not None else cur for new, cur in zip((n_kg_ha, p2o5_kg_ha, k2o_kg_ha), old.npk_kg_ha))
        self._registered[key] = DayDemand(old.water_mm if water_mm is None else float(water_mm), npk)

    def close_day(self) -> DayDemand:
        """Return the summed demand of all registered crops and clear the ledger."""
        entries = list(self._registered.values())
        total = DayDemand(
            water_mm=sum(d.water_mm for d in entries),
            npk_kg_ha=tuple(sum(d.npk_kg_ha[i] for d in entries) for i in range(3)),
        )
        self._registered = {}
        return total


    def pending(self) -> DayDemand:
        """Demand registered so far today, without clearing the ledger."""
        entries = list(self._registered.values())
        return DayDemand(
            water_mm=sum(d.water_mm for d in entries),
            npk_kg_ha=tuple(sum(d.npk_kg_ha[i] for d in entries) for i in range(3)),
        )

    def set_recommended(self, crop_name: str, npk: tuple[float, float, float]) -> None:
        self._recommended[crop_name.strip().lower()] = tuple(npk)

# --------------------------------------------------------------------------- #
# TextureSoilFertilizerModel: facade (day clock + call order)
# Texture-based soil water and fertilizer model (facade).
#
# Replaces the pass-through ``GenericSoilFertilizerModel``. This class owns only
# the day clock and the call order; the physics lives in the components:
#
#     SoilProfile   texture + hydraulics (stateless data)
#     WaterBalance  root-zone water, returns a WaterFlux each day
#     NutrientPools N, P2O5, K2O pools, consume the WaterFlux
#     DemandLedger  per-crop daily demand shared by both
#
# Order inside ``_close_day`` is fixed: demand -> water -> nutrients.
# Days must be requested in non-decreasing order. Call ``initialize`` to start a new run.
#
# Everything marked ASSUMPTION is a placeholder, not a sourced value.
# --------------------------------------------------------------------------- #
class TextureSoilFertilizerModel(SoilFertilizerModel):
    def __init__(
        self,
        soil: str | SoilTexture = "loam",
        nutrients: NutrientApplication | None = None,
        irrigation: IrrigationSchedule | None = None,
        *,
        root_zone_depth_m: float = 0.30,  # ASSUMPTION
        depletion_fraction: float = 0.0,
        initial_water_fraction: float = 1.0,  # share of TAW at the start
        reference_demand_mm_day: float = 4.0,  # ASSUMPTION
        season_days: int = 90,  # fallback, used only when the crop has no growth_days
        recommended_npk: Mapping[str, tuple[float, float, float]] | None = None,
        indigenous_npk_kg_ha: tuple[float, float, float] = (0.0, 0.0, 0.0),
        leaching_mobility: Mapping[str, float] | None = None,  # ASSUMPTION
        nutrient_combination: str = "min",
        tracked_nutrients: Iterable[str] = NUTRIENTS,  # which of "n", "p2o5", "k2o" are modelled
        hydraulic_source: str = "saxton_rawls",
        combine_with_config_factors: bool = True,  # user's water_factor / nutrient_factor scale the result
    ) -> None:
        profile = SoilProfile.build(soil, hydraulic_source)
        # ASSUMPTION: when no application is given, apply the placeholder rates so a forgotten
        # input does not silently stop growth. Pass NutrientApplication(0, 0, 0) for no fertilizer.
        application = nutrients or NutrientApplication(*DEFAULT_RECOMMENDED_NPK)
        self._attach(
            WaterBalance(
                profile,
                irrigation,
                root_zone_depth_m=root_zone_depth_m,
                depletion_fraction=depletion_fraction,
                initial_water_fraction=initial_water_fraction,
            ),
            NutrientPools(
                application,
                indigenous_npk_kg_ha,
                leaching_mobility,
                nutrient_combination,
                tracked_nutrients,
            ),
            DemandLedger(reference_demand_mm_day, season_days, recommended_npk),
            combine_with_config_factors,
        )

    @classmethod
    def from_components(
        cls,
        water_balance: WaterBalance,
        nutrient_pools: NutrientPools,
        demand_ledger: DemandLedger | None = None,
        *,
        combine_with_config_factors: bool = True,  # user's water_factor / nutrient_factor scale the result
    ) -> "TextureSoilFertilizerModel":
        """Build the model from ready-made components (swap in your own nutrient or water part).

        Any object with the same methods works: ``reset``, ``open_day``, ``close_day`` and ``factor``
        (plus ``levels`` / ``cumulative`` if you call ``snapshot``).
        """
        model = cls.__new__(cls)
        model._attach(water_balance, nutrient_pools, demand_ledger or DemandLedger(), combine_with_config_factors)
        return model

    def _attach(self, water_balance, nutrient_pools, demand_ledger, combine_with_config_factors: bool) -> None:
        self.water_balance = water_balance
        self.nutrient_pools = nutrient_pools
        self.demand_ledger = demand_ledger
        self.combine_with_config_factors = combine_with_config_factors
        self._reset()

    # -- read-only views kept for backward compatibility -------------------- #
    @property
    def soil_profile(self) -> SoilProfile:
        return self.water_balance.profile

    @property
    def texture(self) -> SoilTexture:
        return self.water_balance.profile.texture

    @property
    def hydraulics(self):
        return self.water_balance.profile.hydraulics

    @property
    def taw_mm(self) -> float:
        return self.water_balance.taw_mm

    @property
    def gravitational_capacity_mm(self) -> float:
        return self.water_balance.gravitational_capacity_mm

    @property
    def irrigation(self) -> IrrigationSchedule:
        return self.water_balance.irrigation

    @property
    def nutrients(self) -> NutrientApplication:
        return self.nutrient_pools.application

    # -- contract ---------------------------------------------------------- #
    def initialize(self, greenhouse: GreenhouseConfig) -> None:
        self._reset()

    def resources_for_day(
        self,
        crop: CropParameters,
        greenhouse: GreenhouseConfig,
        day_index: int,
    ) -> ResourceAvailability:
        self._advance_to(int(day_index))
        self.demand_ledger.register(crop)  # called directly so its warning points at the caller
        water = self.water_balance.factor(self.demand_ledger.pending().water_mm)
        nutrient = self.nutrient_pools.factor()
        if self.combine_with_config_factors:
            water *= clamp01(getattr(greenhouse, "water_factor", 1.0))
            nutrient *= clamp01(getattr(greenhouse, "nutrient_factor", 1.0))
        return ResourceAvailability(water_factor=clamp01(water), nutrient_factor=clamp01(nutrient))

    # -- optional hooks ---------------------------------------------------- #
    def record_uptake(
        self,
        day_index: int,
        crop_name: str,
        water_mm: float | None = None,
        n_kg_ha: float | None = None,
        p2o5_kg_ha: float | None = None,
        k2o_kg_ha: float | None = None,
    ) -> None:
        """Replace the fallback demand of a crop on the current day with the engine's own figures."""
        if int(day_index) != self._day:
            raise ValueError("uptake can only be recorded for the current day")
        self.demand_ledger.record_uptake(crop_name, water_mm, n_kg_ha, p2o5_kg_ha, k2o_kg_ha)

    def snapshot(self) -> dict[str, float]:
        """Current state and cumulative totals, for logging and plots."""
        wb, npk = self.water_balance, self.nutrient_pools
        levels = npk.levels()
        cumulative = {**wb.cumulative(), **npk.cumulative()}
        return {
            "day": self._day,
            "available_water_mm": wb.available_water_mm,
            "total_available_water_mm": wb.taw_mm,
            "gravitational_water_mm": wb.gravitational_mm,
            "n_kg_ha": levels["n"],
            "p2o5_kg_ha": levels["p2o5"],
            "k2o_kg_ha": levels["k2o"],
            "water_factor": wb.factor(),
            "nutrient_factor": npk.factor(),
            **{f"cum_{k}": v for k, v in cumulative.items()},
        }

    # -- day clock (the only place days advance) --------------------------- #
    def _reset(self) -> None:
        self._day = -1
        self.water_balance.reset()
        self.nutrient_pools.reset()
        self.demand_ledger.reset()

    def _advance_to(self, day: int) -> None:
        if day < self._day:
            raise ValueError("days must be requested in non-decreasing order; call initialize() for a new run")
        while self._day < day:
            if self._day >= 0:
                self._close_day()
            self._day += 1
            self._open_day(self._day)

    def _open_day(self, day: int) -> None:
        self.nutrient_pools.open_day(day)
        self.water_balance.open_day(day)

    def _close_day(self) -> None:
        demand = self.demand_ledger.close_day()
        flux = self.water_balance.close_day(demand.water_mm)  # water first
        self.nutrient_pools.close_day(demand.npk_kg_ha, flux)  # nutrients consume the flux