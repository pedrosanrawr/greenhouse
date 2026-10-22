"""Fruit yield model: crops picked repeatedly (tomato, pepper, cucumber, ...).

What it models (all in grams of dry mass per plant, like the rest of the engine):

* Fruit growth is taken from the engine's own decision: the day's granted growth
  times the phase's fruit share of the biomass ratio. This model does not grow
  fruit; it decides what happens to fruit once it exists.
* Fruit set (temperature): above a heat onset temperature a growing share of the
  day's new fruit mass fails to set. Failed fruit stays in the fruit pool as
  unharvestable mass (there is no abscission in the engine yet).
* Ripening (temperature): each day's set fruit is a cohort that ripens after
  it has accumulated a fixed amount of thermal time.
* Quality (water): fruit set on days with a low water factor loses part of its
  marketable mass (a stand-in for blossom-end rot and cracking). The lost part
  stays on the plant, unharvested.
* Harvest: from first_harvest_min_days, on a fixed interval, all ripe
  marketable fruit is picked. The engine removes it from the fruit organ and
  keeps a cumulative total.

Every default in FruitYieldParameters is a tomato-like TEST VALUE. None is
sourced or calibrated, and none should be quoted as crop physiology. Another
fruit crop should pass its own FruitYieldParameters, with a cited source
beside each value.

Not modelled yet: cold-limited fruit set, day/night temperature split (the
environment gives one mean temperature), nutrient effects on yield (the
nutrient factor is available in the context but unused here), fruit size, and
fruit pruning. The model relies on the plant file's biomass_ratio and
phase_start_days for when fruit is grown.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from data.models.contracts import YieldModel
from data.models.types import (
    CropParameters,
    CropState,
    GreenhouseConfig,
    YieldContext,
    YieldState,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class FruitYieldParameters:
    # ---- ripening: thermal time from fruit set to ripe
    ripening_base_c: float = 10.0  # TEST VALUE: base temperature for ripening
    ripening_degree_days: float = 500.0  # TEST VALUE: degree-days from set to ripe

    # ---- fruit set under heat: 1.0 up to onset, falling linearly to the minimum at the limit
    heat_onset_c: float = 26.0  # TEST VALUE
    heat_limit_c: float = 32.0  # TEST VALUE
    heat_min_set_fraction: float = 0.2  # TEST VALUE: share that still sets at/above the limit

    # ---- quality under water stress: no loss at or above the threshold,
    #      loss grows linearly to max_quality_loss at a water factor of 0
    water_quality_threshold: float = 0.8  # TEST VALUE
    max_quality_loss: float = 0.3  # TEST VALUE

    # ---- harvest rhythm
    harvest_interval_days: int = 7  # TEST VALUE: weekly picking

    def __post_init__(self) -> None:
        numbers = (
            self.ripening_base_c, self.ripening_degree_days, self.heat_onset_c,
            self.heat_limit_c, self.heat_min_set_fraction,
            self.water_quality_threshold, self.max_quality_loss,
            self.harvest_interval_days,
        )
        if not all(math.isfinite(v) for v in numbers):
            raise ValueError("tomato yield parameters must be finite")
        if self.ripening_degree_days <= 0.0:
            raise ValueError("ripening_degree_days must be positive")
        if not self.heat_onset_c < self.heat_limit_c:
            raise ValueError("heat_onset_c must be below heat_limit_c")
        if not 0.0 <= self.heat_min_set_fraction <= 1.0:
            raise ValueError("heat_min_set_fraction must be in [0, 1]")
        if not 0.0 < self.water_quality_threshold <= 1.0:
            raise ValueError("water_quality_threshold must be in (0, 1]")
        if not 0.0 <= self.max_quality_loss <= 1.0:
            raise ValueError("max_quality_loss must be in [0, 1]")
        if (
            int(self.harvest_interval_days) != self.harvest_interval_days
            or self.harvest_interval_days < 1
        ):
            raise ValueError("harvest_interval_days must be a whole number >= 1")


@dataclass
class _Cohort:
    """Fruit set on one day: its dry mass, marketable share and ripening progress."""

    mass_g: float
    quality: float
    thermal_time: float = 0.0


class FruitYieldModel(YieldModel):
    def __init__(self, parameters: FruitYieldParameters | None = None) -> None:
        self.parameters = parameters or FruitYieldParameters()
        self._reset()

    # -- per-run state ------------------------------------------------------ #
    def _reset(self) -> None:
        self._cohorts: list[_Cohort] = []
        self._next_day = 0
        self._last_harvest_day: int | None = None
        self._aborted_total_g = 0.0
        self._heat_stress_days = 0

    def initialize(self, crop: CropParameters, greenhouse: GreenhouseConfig) -> None:
        self._reset()

    # -- response functions -------------------------------------------------- #
    def fruit_set_fraction(self, temperature_c: float) -> float:
        p = self.parameters
        if temperature_c <= p.heat_onset_c:
            return 1.0
        if temperature_c >= p.heat_limit_c:
            return p.heat_min_set_fraction
        progress = (temperature_c - p.heat_onset_c) / (p.heat_limit_c - p.heat_onset_c)
        return 1.0 - progress * (1.0 - p.heat_min_set_fraction)

    def quality_fraction(self, water_factor: float) -> float:
        p = self.parameters
        water = _clamp01(water_factor)
        if water >= p.water_quality_threshold:
            return 1.0
        shortfall = (p.water_quality_threshold - water) / p.water_quality_threshold
        return 1.0 - p.max_quality_loss * shortfall

    # -- contract ------------------------------------------------------------ #
    def estimate_yield(
        self,
        crop: CropParameters,
        state: CropState,
        day_index: int,
        context: YieldContext | None = None,
    ) -> YieldState:
        if context is None:
            raise ValueError("FruitYieldModel needs a YieldContext from the engine")
        if day_index != self._next_day:
            raise ValueError(
                f"days must be requested in order (expected {self._next_day}, "
                f"got {day_index}); call initialize() for a new run"
            )
        self._next_day += 1
        p = self.parameters

        temperature = context.environment.temperature_c
        water_factor = context.resources.water_factor

        # 1. New fruit mass today: the same split the engine just applied.
        fruit_share = crop.ratio_for(context.phase).get("fruit", 0.0)
        new_fruit_g = max(0.0, context.granted_growth_g) * fruit_share

        # 2. Heat stress decides how much of it sets; the rest stays unharvestable.
        set_fraction = self.fruit_set_fraction(temperature)
        set_g = new_fruit_g * set_fraction
        self._aborted_total_g += new_fruit_g - set_g
        if new_fruit_g > 0.0 and set_fraction < 1.0:
            self._heat_stress_days += 1

        # 3. Existing cohorts ripen; today's cohort starts at zero thermal time.
        degree_days = max(0.0, temperature - p.ripening_base_c)
        for cohort in self._cohorts:
            cohort.thermal_time += degree_days
        quality = self.quality_fraction(water_factor)
        if set_g > 0.0:
            self._cohorts.append(_Cohort(set_g, quality))

        # 4. What is ripe and marketable right now.
        ripe = [c for c in self._cohorts if c.thermal_time >= p.ripening_degree_days]
        ripe_marketable_g = sum(c.mass_g * c.quality for c in ripe)
        past_first_harvest = (day_index + 1) >= crop.first_harvest_min_days
        standing_g = ripe_marketable_g if past_first_harvest else 0.0

        # 5. Harvest on schedule: pick every ripe cohort.
        harvested_g = 0.0
        due = (
            self._last_harvest_day is None
            or day_index - self._last_harvest_day >= p.harvest_interval_days
        )
        if past_first_harvest and due and standing_g > 0.0:
            harvested_g = standing_g
            self._last_harvest_day = day_index
            # Picked cohorts leave tracking. Their unmarketable share (mass x
            # (1 - quality)) stays on the plant as unharvestable fruit mass.
            picked = {id(c) for c in ripe}
            self._cohorts = [c for c in self._cohorts if id(c) not in picked]

        unripe_g = sum(c.mass_g for c in self._cohorts)
        return YieldState(
            harvestable_biomass_g=standing_g,
            yield_ready=standing_g > 0.0,
            harvested_biomass_g=harvested_g,
            diagnostics={
                "fruit_set_fraction": set_fraction,
                "quality_fraction": quality,
                "unripe_fruit_g": unripe_g,
                "aborted_total_g": self._aborted_total_g,
                "heat_stress_days": float(self._heat_stress_days),
            },
        )