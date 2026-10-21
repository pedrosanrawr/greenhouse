"""Greenlab compatibility score.

A scenario suitability index (0 to 1) for how well a run's crops suit the
run's environment. It is computed from dataset requirements only, never from
simulated biomass or yield.

This module is pure: no Streamlit and no engine imports.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

# ============================================================
# CONFIGURATION (provisional, uncalibrated)
# ============================================================

DEFAULT_WEIGHTS = {"temperature": 0.6, "cycle": 0.2, "light": 0.2}
VALID_WEIGHT_KEYS = frozenset(DEFAULT_WEIGHTS)

# Group score = share * mean + (1 - share) * min, over scored crops.
GROUP_MEAN_SHARE = 0.5

# A group score needs at least this many scored crops.
MIN_SCORED_CROPS = 2

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


@dataclass(frozen=True)
class CompatibilityResult:
    group_score: float | None
    mean_score: float | None
    min_score: float | None
    weakest_crop: str | None
    optimal_band_overlap_c: tuple[float, float] | None
    crops: tuple[CropCompatibility, ...]


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


def validate_crop_requirements(
    *,
    t_abs_min=None,
    t_opt_min=None,
    t_opt_max=None,
    t_abs_max=None,
    dli_min=None,
    dli_opt=None,
    temperature_band_verified=False,
):
    """Validate the compatibility fields of a crop. Raises ValueError.

    Called from CropParameters.__post_init__ so the rules live in one
    place and can be tested without constructing a full crop.
    """
    temps = {
        "t_abs_min": t_abs_min,
        "t_opt_min": t_opt_min,
        "t_opt_max": t_opt_max,
        "t_abs_max": t_abs_max,
    }
    dli = {"dli_min": dli_min, "dli_opt": dli_opt}

    for name, value in {**temps, **dli}.items():
        if value is not None:
            _finite(name, value)

    set_count = sum(value is not None for value in temps.values())
    if 0 < set_count < 4:
        raise ValueError(
            "Set all four temperature fields (t_abs_min, t_opt_min, "
            "t_opt_max, t_abs_max) or none of them."
        )
    if set_count == 4 and not (
        t_abs_min < t_opt_min <= t_opt_max < t_abs_max
    ):
        raise ValueError(
            "Temperature band must satisfy "
            "t_abs_min < t_opt_min <= t_opt_max < t_abs_max."
        )
    if temperature_band_verified and set_count < 4:
        raise ValueError(
            "temperature_band_verified is True but the temperature band "
            "is incomplete."
        )

    if (dli_min is None) != (dli_opt is None):
        raise ValueError("Set both dli_min and dli_opt, or neither.")
    if dli_min is not None and not (0 < dli_min < dli_opt):
        raise ValueError("DLI fields must satisfy 0 < dli_min < dli_opt.")


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
        raise ValueError(
            "No available sub-score has a weight above 0."
        )

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


def crop_compatibility(
    params,
    temperature_c,
    run_days,
    mean_dli=None,
    weights=DEFAULT_WEIGHTS,
    name=None,
) -> CropCompatibility:
    _validate_weights(weights)
    temperature_c = _finite("temperature_c", temperature_c)
    run_days = _finite("run_days", run_days)
    if run_days < 1:
        raise ValueError("run_days must be at least 1.")
    if mean_dli is not None:
        mean_dli = _finite("mean_dli", mean_dli)

    crop_name = name or str(getattr(params, "name", "unknown"))
    band = _temperature_band(params)
    dli_min = getattr(params, "dli_min", None)
    dli_opt = getattr(params, "dli_opt", None)
    verified = bool(getattr(params, "temperature_band_verified", False))

    validate_crop_requirements(
        t_abs_min=band[0],
        t_opt_min=band[1],
        t_opt_max=band[2],
        t_abs_max=band[3],
        dli_min=dli_min,
        dli_opt=dli_opt,
        temperature_band_verified=verified,
    )

    # Eligibility gate: never impute a missing or unverified band.
    if any(value is None for value in band):
        return CropCompatibility(
            crop_name, None, None, None, None, REASON_BAND_MISSING
        )
    if not verified:
        return CropCompatibility(
            crop_name, None, None, None, None, REASON_BAND_UNVERIFIED
        )

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

    score = combine_scores(
        {"temperature": temperature, "cycle": cycle, "light": light},
        weights,
    )
    return CropCompatibility(
        crop_name, score, temperature, cycle, light, None
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
) -> CompatibilityResult:
    _validate_weights(weights)
    named = _named_crops(crops)

    results = tuple(
        crop_compatibility(
            params, temperature_c, run_days, mean_dli, weights, name=name
        )
        for name, params in named
    )
    params_by_name = dict(named)
    scored = [result for result in results if result.score is not None]

    if len(scored) < MIN_SCORED_CROPS:
        return CompatibilityResult(None, None, None, None, None, results)

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
    )