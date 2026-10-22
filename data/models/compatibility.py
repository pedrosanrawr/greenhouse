"""Greenlab compatibility score.

A scenario suitability index (0 to 1) for how well a run's crops suit the
run's environment. It is computed from dataset requirements and the user's
inputs only, never from simulated biomass, yield or simulated growth factors.

Sub-scores: temperature, cycle, light, water, nutrient.

This module is pure: no Streamlit and no engine imports.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from data.models.water_budget import (
    WaterAllocation,
    allocate_water_budget,
    water_band_mm_day,
    water_requirement_mm_day,
)

# ============================================================
# CONFIGURATION (provisional, uncalibrated)
# ============================================================

# Weights are renormalized over the sub-scores that are available, so a crop
# without water or nutrient data scores exactly as it did before they existed.
DEFAULT_WEIGHTS = {
    "temperature": 0.6,
    "cycle": 0.2,
    "light": 0.2,
    "water": 0.2,
    "nutrient": 0.2,
}
VALID_WEIGHT_KEYS = frozenset(DEFAULT_WEIGHTS)

# Group score = share * mean + (1 - share) * min, over scored crops.
GROUP_MEAN_SHARE = 0.5

# A group score needs at least this many scored crops.
MIN_SCORED_CROPS = 2

NUTRIENT_KEYS = ("n", "p2o5", "k2o")

REASON_BAND_MISSING = "temperature band missing"
REASON_BAND_UNVERIFIED = "temperature band not verified"


# ============================================================
# RESULT TYPES
# ============================================================

@dataclass(frozen=True)
class CropCompatibility:
    crop: str
    score: float | None  # None = not scored
    temperature: float | None
    cycle: float | None
    light: float | None
    excluded_reason: str | None
    water: float | None = None
    nutrient: float | None = None
    water_supply_mm_day: float | None = None
    water_requirement_mm_day: float | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompatibilityResult:
    group_score: float | None
    mean_score: float | None
    min_score: float | None
    weakest_crop: str | None
    optimal_band_overlap_c: tuple[float, float] | None
    crops: tuple[CropCompatibility, ...]
    water_allocation: WaterAllocation | None = None


# ============================================================
# VALIDATION
# ============================================================

def _finite(name, value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _validate_temperature_and_light(
    t_abs_min, t_opt_min, t_opt_max, t_abs_max, dli_min, dli_opt, verified
):
    temps = {
        "t_abs_min": t_abs_min,
        "t_opt_min": t_opt_min,
        "t_opt_max": t_opt_max,
        "t_abs_max": t_abs_max,
    }
    set_count = sum(value is not None for value in temps.values())
    if 0 < set_count < 4:
        raise ValueError(
            "Set all four temperature fields (t_abs_min, t_opt_min, "
            "t_opt_max, t_abs_max) or none of them."
        )
    if set_count == 4 and not (t_abs_min < t_opt_min <= t_opt_max < t_abs_max):
        raise ValueError(
            "Temperature band must satisfy "
            "t_abs_min < t_opt_min <= t_opt_max < t_abs_max."
        )
    if verified and set_count < 4:
        raise ValueError(
            "temperature_band_verified is True but the temperature band "
            "is incomplete."
        )

    if (dli_min is None) != (dli_opt is None):
        raise ValueError("Set both dli_min and dli_opt, or neither.")
    if dli_min is not None and not (0 < dli_min < dli_opt):
        raise ValueError("DLI fields must satisfy 0 < dli_min < dli_opt.")


def _validate_water(abs_min, opt_min, opt_max, abs_max, cycle_days, verified):
    values = (abs_min, opt_min, opt_max, abs_max, cycle_days)
    set_count = sum(value is not None for value in values)
    if 0 < set_count < 5:
        raise ValueError(
            "Set all water fields (four band values in mm per cycle plus "
            "water_cycle_days) or none of them."
        )
    if set_count == 5:
        if not (0 <= abs_min < opt_min <= opt_max < abs_max):
            raise ValueError(
                "Water band must satisfy "
                "0 <= abs_min < opt_min <= opt_max < abs_max."
            )
        if cycle_days <= 0:
            raise ValueError("water_cycle_days must be positive.")
    if verified and set_count < 5:
        raise ValueError(
            "water_band_verified is True but the water band is incomplete."
        )


def _validate_nutrients(rates, verified):
    """rates: {key: (rec_min, rec_max, excess)}"""
    for key, (low, high, excess) in rates.items():
        if (low is None) != (high is None):
            raise ValueError(
                f"Set both {key}_rec_min_kg_ha and {key}_rec_max_kg_ha, or neither."
            )
        if low is not None and not (0 < low <= high):
            raise ValueError(
                f"{key} rates must satisfy 0 < rec_min <= rec_max."
            )
        if excess is not None:
            if low is None:
                raise ValueError(f"{key}_excess_kg_ha needs the recommended range.")
            if not excess > high:
                raise ValueError(f"{key}_excess_kg_ha must exceed rec_max.")
    if verified and any(low is None for low, _, _ in rates.values()):
        raise ValueError(
            "nutrient_rates_verified is True but N, P2O5 and K2O ranges "
            "are not all set."
        )


def validate_crop_requirements(
    *,
    t_abs_min=None,
    t_opt_min=None,
    t_opt_max=None,
    t_abs_max=None,
    dli_min=None,
    dli_opt=None,
    temperature_band_verified=False,
    water_abs_min_mm=None,
    water_opt_min_mm=None,
    water_opt_max_mm=None,
    water_abs_max_mm=None,
    water_cycle_days=None,
    water_band_verified=False,
    n_rec_min_kg_ha=None,
    n_rec_max_kg_ha=None,
    n_excess_kg_ha=None,
    p2o5_rec_min_kg_ha=None,
    p2o5_rec_max_kg_ha=None,
    p2o5_excess_kg_ha=None,
    k2o_rec_min_kg_ha=None,
    k2o_rec_max_kg_ha=None,
    k2o_excess_kg_ha=None,
    nutrient_rates_verified=False,
):
    """Validate the compatibility fields of a crop. Raises ValueError.

    Called from CropParameters.__post_init__ (through validate_crop_params)
    so the rules live in one place and can be tested without a full crop.
    """
    numeric = {
        "t_abs_min": t_abs_min, "t_opt_min": t_opt_min,
        "t_opt_max": t_opt_max, "t_abs_max": t_abs_max,
        "dli_min": dli_min, "dli_opt": dli_opt,
        "water_abs_min_mm": water_abs_min_mm,
        "water_opt_min_mm": water_opt_min_mm,
        "water_opt_max_mm": water_opt_max_mm,
        "water_abs_max_mm": water_abs_max_mm,
        "water_cycle_days": water_cycle_days,
        "n_rec_min_kg_ha": n_rec_min_kg_ha, "n_rec_max_kg_ha": n_rec_max_kg_ha,
        "n_excess_kg_ha": n_excess_kg_ha,
        "p2o5_rec_min_kg_ha": p2o5_rec_min_kg_ha,
        "p2o5_rec_max_kg_ha": p2o5_rec_max_kg_ha,
        "p2o5_excess_kg_ha": p2o5_excess_kg_ha,
        "k2o_rec_min_kg_ha": k2o_rec_min_kg_ha,
        "k2o_rec_max_kg_ha": k2o_rec_max_kg_ha,
        "k2o_excess_kg_ha": k2o_excess_kg_ha,
    }
    for name, value in numeric.items():
        if value is not None:
            _finite(name, value)

    _validate_temperature_and_light(
        t_abs_min, t_opt_min, t_opt_max, t_abs_max,
        dli_min, dli_opt, temperature_band_verified,
    )
    _validate_water(
        water_abs_min_mm, water_opt_min_mm, water_opt_max_mm,
        water_abs_max_mm, water_cycle_days, water_band_verified,
    )
    _validate_nutrients(
        {
            "n": (n_rec_min_kg_ha, n_rec_max_kg_ha, n_excess_kg_ha),
            "p2o5": (p2o5_rec_min_kg_ha, p2o5_rec_max_kg_ha, p2o5_excess_kg_ha),
            "k2o": (k2o_rec_min_kg_ha, k2o_rec_max_kg_ha, k2o_excess_kg_ha),
        },
        nutrient_rates_verified,
    )


_BOOL_FIELDS = frozenset(
    {"temperature_band_verified", "water_band_verified", "nutrient_rates_verified"}
)
_REQUIREMENT_FIELDS = (
    "t_abs_min", "t_opt_min", "t_opt_max", "t_abs_max",
    "dli_min", "dli_opt", "temperature_band_verified",
    "water_abs_min_mm", "water_opt_min_mm", "water_opt_max_mm",
    "water_abs_max_mm", "water_cycle_days", "water_band_verified",
    "n_rec_min_kg_ha", "n_rec_max_kg_ha", "n_excess_kg_ha",
    "p2o5_rec_min_kg_ha", "p2o5_rec_max_kg_ha", "p2o5_excess_kg_ha",
    "k2o_rec_min_kg_ha", "k2o_rec_max_kg_ha", "k2o_excess_kg_ha",
    "nutrient_rates_verified",
)


def validate_crop_params(params):
    """Validate every compatibility field found on a crop object."""
    validate_crop_requirements(
        **{
            field: getattr(params, field, False if field in _BOOL_FIELDS else None)
            for field in _REQUIREMENT_FIELDS
        }
    )


def _validate_weights(weights):
    if not isinstance(weights, Mapping):
        raise ValueError("weights must be a mapping.")
    unknown = set(weights) - VALID_WEIGHT_KEYS
    if unknown:
        raise ValueError(
            f"Unknown weight key(s): {sorted(unknown)}. "
            f"Allowed: {sorted(VALID_WEIGHT_KEYS)}."
        )
    for key, value in weights.items():
        if _finite(f"weight {key!r}", value) < 0:
            raise ValueError(f"Weight {key!r} must be non-negative.")


# ============================================================
# SUB-SCORES
# ============================================================

def trapezoid_score(x, a_min, o_min, o_max, a_max) -> float:
    x = _finite("x", x)
    a_min = _finite("a_min", a_min)
    o_min = _finite("o_min", o_min)
    o_max = _finite("o_max", o_max)
    a_max = _finite("a_max", a_max)

    if not (a_min < o_min <= o_max < a_max):
        raise ValueError(
            "Band must satisfy a_min < o_min <= o_max < a_max, got "
            f"{a_min}, {o_min}, {o_max}, {a_max}."
        )

    if x <= a_min or x >= a_max:
        return 0.0
    if x < o_min:
        return (x - a_min) / (o_min - a_min)
    if x <= o_max:
        return 1.0
    return (a_max - x) / (a_max - o_max)


def ramp_score(x, low, high) -> float:
    x = _finite("x", x)
    low = _finite("low", low)
    high = _finite("high", high)

    if not low < high:
        raise ValueError(f"Ramp needs low < high, got {low} and {high}.")

    if x <= low:
        return 0.0
    if x >= high:
        return 1.0
    return (x - low) / (high - low)


def cycle_score(run_days, first_harvest_min_days) -> float:
    run_days = _finite("run_days", run_days)
    first = _finite("first_harvest_min_days", first_harvest_min_days)

    if run_days < 1:
        raise ValueError("run_days must be at least 1.")
    if first <= 0:
        raise ValueError("first_harvest_min_days must be positive.")

    return min(1.0, run_days / first)


def nutrient_score(applied, rec_min, rec_max, excess=None) -> float:
    """One nutrient: ramp up to rec_min, flat to rec_max, then (optionally) down to 0 at excess.

    With no excess limit the score stays at 1 above rec_max.
    """
    applied = _finite("applied", applied)
    rec_min = _finite("rec_min", rec_min)
    rec_max = _finite("rec_max", rec_max)

    if applied < 0:
        raise ValueError("Applied nutrient amount cannot be negative.")
    if not 0 < rec_min <= rec_max:
        raise ValueError("Needs 0 < rec_min <= rec_max.")

    if applied < rec_min:
        return applied / rec_min
    if applied <= rec_max or excess is None:
        return 1.0

    excess = _finite("excess", excess)
    if not excess > rec_max:
        raise ValueError("excess must exceed rec_max.")
    if applied >= excess:
        return 0.0
    return (excess - applied) / (excess - rec_max)


# ============================================================
# COMBINING
# ============================================================

def combine_scores(subscores, weights=DEFAULT_WEIGHTS) -> float:
    """Weighted geometric mean over the available sub-scores.

    A sub-score is available when it is not None and its weight is > 0.
    Weights are renormalized over the available sub-scores.
    """
    _validate_weights(weights)

    available = {}
    for key, score in subscores.items():
        if score is None or weights.get(key, 0) <= 0:
            continue
        score = _finite(f"sub-score {key!r}", score)
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Sub-score {key!r} must be in [0, 1].")
        available[key] = score

    if not available:
        raise ValueError("No available sub-score has a weight above 0.")

    total_weight = sum(weights[key] for key in available)
    result = 1.0
    for key, score in available.items():
        result *= score ** (weights[key] / total_weight)
    return result


# ============================================================
# PER-CROP AND PER-RUN SCORING
# ============================================================

def _temperature_band(params):
    return tuple(
        getattr(params, field, None)
        for field in ("t_abs_min", "t_opt_min", "t_opt_max", "t_abs_max")
    )


def nutrient_rates(params):
    """Verified {key: (rec_min, rec_max, excess)} for N, P2O5, K2O, or None."""
    rates = {
        key: (
            getattr(params, f"{key}_rec_min_kg_ha", None),
            getattr(params, f"{key}_rec_max_kg_ha", None),
            getattr(params, f"{key}_excess_kg_ha", None),
        )
        for key in NUTRIENT_KEYS
    }
    if any(low is None or high is None for low, high, _ in rates.values()):
        return None
    if not getattr(params, "nutrient_rates_verified", False):
        return None
    return rates


def _water_unavailable_reason(params):
    fields = (
        "water_abs_min_mm", "water_opt_min_mm", "water_opt_max_mm",
        "water_abs_max_mm", "water_cycle_days",
    )
    if any(getattr(params, field, None) is None for field in fields):
        return "band missing"
    return "band not verified"


def _nutrient_unavailable_reason(params):
    for key in NUTRIENT_KEYS:
        if (
            getattr(params, f"{key}_rec_min_kg_ha", None) is None
            or getattr(params, f"{key}_rec_max_kg_ha", None) is None
        ):
            return "rates missing"
    return "rates not verified"


def _check_nutrient_supply(supply):
    values = tuple(supply)
    if len(values) != 3:
        raise ValueError("nutrient_supply_kg_ha must be (N, P2O5, K2O).")
    values = tuple(_finite("nutrient supply", v) for v in values)
    if min(values) < 0:
        raise ValueError("Nutrient supply cannot be negative.")
    return values


def crop_compatibility(
    params,
    temperature_c,
    run_days,
    mean_dli=None,
    weights=DEFAULT_WEIGHTS,
    name=None,
    water_supply_mm_day=None,
    nutrient_supply_kg_ha=None,
) -> CropCompatibility:
    _validate_weights(weights)
    temperature_c = _finite("temperature_c", temperature_c)
    run_days = _finite("run_days", run_days)
    if run_days < 1:
        raise ValueError("run_days must be at least 1.")
    if mean_dli is not None:
        mean_dli = _finite("mean_dli", mean_dli)
    if water_supply_mm_day is not None:
        water_supply_mm_day = _finite("water_supply_mm_day", water_supply_mm_day)
        if water_supply_mm_day < 0:
            raise ValueError("water_supply_mm_day cannot be negative.")
    if nutrient_supply_kg_ha is not None:
        nutrient_supply_kg_ha = _check_nutrient_supply(nutrient_supply_kg_ha)

    crop_name = name or str(getattr(params, "name", "unknown"))
    validate_crop_params(params)

    band = _temperature_band(params)
    dli_min = getattr(params, "dli_min", None)
    dli_opt = getattr(params, "dli_opt", None)
    verified = bool(getattr(params, "temperature_band_verified", False))
    requirement = water_requirement_mm_day(params)

    def excluded(reason):
        return CropCompatibility(
            crop_name, None, None, None, None, reason,
            water_supply_mm_day=water_supply_mm_day,
            water_requirement_mm_day=requirement,
        )

    # Eligibility gate: never impute a missing or unverified band.
    if any(value is None for value in band):
        return excluded(REASON_BAND_MISSING)
    if not verified:
        return excluded(REASON_BAND_UNVERIFIED)

    temperature = trapezoid_score(temperature_c, *band)

    first_harvest = getattr(params, "first_harvest_min_days", None)
    cycle = (
        cycle_score(run_days, first_harvest)
        if first_harvest is not None
        else None
    )

    light = None
    if dli_min is not None and dli_opt is not None and mean_dli is not None:
        light = ramp_score(mean_dli, dli_min, dli_opt)

    notes = []

    water = None
    if water_supply_mm_day is not None:
        water_band = water_band_mm_day(params)
        if water_band is None:
            notes.append(f"water not scored ({_water_unavailable_reason(params)})")
        else:
            water = trapezoid_score(water_supply_mm_day, *water_band)

    nutrient = None
    if nutrient_supply_kg_ha is not None:
        rates = nutrient_rates(params)
        if rates is None:
            notes.append(
                f"nutrients not scored ({_nutrient_unavailable_reason(params)})"
            )
        else:
            # The scarcest (or most excessive) nutrient limits the score.
            nutrient = min(
                nutrient_score(applied, *rates[key])
                for applied, key in zip(nutrient_supply_kg_ha, NUTRIENT_KEYS)
            )

    score = combine_scores(
        {
            "temperature": temperature,
            "cycle": cycle,
            "light": light,
            "water": water,
            "nutrient": nutrient,
        },
        weights,
    )
    return CropCompatibility(
        crop_name, score, temperature, cycle, light, None,
        water=water,
        nutrient=nutrient,
        water_supply_mm_day=water_supply_mm_day,
        water_requirement_mm_day=requirement,
        notes=tuple(notes),
    )


def _named_crops(crops):
    """Accept {name: params} or a sequence of params objects with .name."""
    if isinstance(crops, Mapping):
        return list(crops.items())
    return [
        (str(getattr(params, "name", f"crop {index + 1}")), params)
        for index, params in enumerate(crops)
    ]


def score_run(
    crops,
    temperature_c,
    run_days,
    mean_dli=None,
    weights=DEFAULT_WEIGHTS,
    water_budget_mm_day=None,
    nutrient_supply_kg_ha=None,
) -> CompatibilityResult:
    """Score a group of crops.

    water_budget_mm_day is the shared budget for the whole group; it is
    split between all selected crops by requirement (see water_budget.py).
    nutrient_supply_kg_ha is (N, P2O5, K2O) applied to each crop.
    """
    _validate_weights(weights)
    named = _named_crops(crops)

    allocation = None
    supplies = {}
    if water_budget_mm_day is not None:
        allocation = allocate_water_budget(
            water_budget_mm_day,
            {name: water_requirement_mm_day(params) for name, params in named},
        )
        supplies = allocation.supply_mm_day

    results = tuple(
        crop_compatibility(
            params, temperature_c, run_days, mean_dli, weights,
            name=name,
            water_supply_mm_day=supplies.get(name),
            nutrient_supply_kg_ha=nutrient_supply_kg_ha,
        )
        for name, params in named
    )
    params_by_name = dict(named)
    scored = [result for result in results if result.score is not None]

    if len(scored) < MIN_SCORED_CROPS:
        return CompatibilityResult(
            None, None, None, None, None, results, water_allocation=allocation
        )

    scores = [result.score for result in scored]
    mean_score = sum(scores) / len(scores)
    min_score = min(scores)
    weakest = min(scored, key=lambda result: result.score).crop
    group = GROUP_MEAN_SHARE * mean_score + (1 - GROUP_MEAN_SHARE) * min_score

    bands = [_temperature_band(params_by_name[r.crop]) for r in scored]
    overlap_low = max(band[1] for band in bands)
    overlap_high = min(band[2] for band in bands)
    overlap = (
        (overlap_low, overlap_high) if overlap_low <= overlap_high else None
    )

    return CompatibilityResult(
        group_score=group,
        mean_score=mean_score,
        min_score=min_score,
        weakest_crop=weakest,
        optimal_band_overlap_c=overlap,
        crops=results,
        water_allocation=allocation,
    )