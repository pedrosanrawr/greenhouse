"""Shared greenhouse water budget.

The user sets one daily water budget (mm/day, 1 mm = 1 L/m2) for the whole
greenhouse. It is split between the selected crops in proportion to each
crop's daily water requirement:

    supply_i = budget * requirement_i / sum(requirement)

so every crop receives the same share of what it needs
(coverage = budget / sum(requirement)).

Pure module: no Streamlit, engine or soil imports.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

# Placeholder used for a crop with no verified water band. Matches the soil
# model's own reference demand (4 mm/day x coefficient 1.0).
DEFAULT_WATER_DEMAND_MM_DAY = 4.0

_BAND_FIELDS = (
    "water_abs_min_mm",
    "water_opt_min_mm",
    "water_opt_max_mm",
    "water_abs_max_mm",
)


def water_band_mm_day(params, *, allow_unverified=False):
    """Verified water band as (abs min, opt min, opt max, abs max) in mm/day.

    The dataset stores mm per crop cycle; this divides by water_cycle_days.
    Returns None when the band is incomplete or not verified, so unverified
    data is never used.
    """
    values = [getattr(params, field, None) for field in _BAND_FIELDS]
    days = getattr(params, "water_cycle_days", None)
    if any(value is None for value in values) or days is None:
        return None
    if (
        not allow_unverified
        and not getattr(params, "water_band_verified", False)
    ):
        return None
    return tuple(value / days for value in values)

def water_requirement_mm_day(params, *, allow_unverified=False):
    """Daily water requirement: midpoint of the optimal band, in mm/day."""
    band = water_band_mm_day(
        params,
        allow_unverified=allow_unverified,
    )
    if band is None:
        return None
    return (band[1] + band[2]) / 2

@dataclass(frozen=True)
class WaterAllocation:
    budget_mm_day: float
    total_requirement_mm_day: float
    coverage: float  # budget / total requirement (1.0 = exactly enough)
    requirement_mm_day: Mapping[str, float]  # effective, defaults filled in
    supply_mm_day: Mapping[str, float]
    defaulted: tuple[str, ...]  # crops using the placeholder requirement


def allocate_water_budget(budget_mm_day, requirements) -> WaterAllocation:
    """Split a daily budget across crops by requirement.

    requirements maps crop name -> mm/day, or None for "no verified band"
    (the placeholder DEFAULT_WATER_DEMAND_MM_DAY is used for those).
    """
    try:
        budget = float(budget_mm_day)
    except (TypeError, ValueError):
        raise ValueError(f"budget must be a number, got {budget_mm_day!r}") from None
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("budget must be finite and non-negative.")

    effective, defaulted = {}, []
    for name, requirement in requirements.items():
        if requirement is None:
            effective[name] = DEFAULT_WATER_DEMAND_MM_DAY
            defaulted.append(name)
            continue
        requirement = float(requirement)
        if not math.isfinite(requirement) or requirement <= 0:
            raise ValueError(f"Requirement for {name!r} must be positive.")
        effective[name] = requirement

    if not effective:
        return WaterAllocation(budget, 0.0, 0.0, {}, {}, ())

    total = sum(effective.values())
    return WaterAllocation(
        budget_mm_day=budget,
        total_requirement_mm_day=total,
        coverage=budget / total,
        requirement_mm_day=effective,
        supply_mm_day={
            name: budget * requirement / total
            for name, requirement in effective.items()
        },
        defaulted=tuple(defaulted),
    )