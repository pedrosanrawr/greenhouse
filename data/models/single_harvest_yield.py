"""Fallback yield models for crops harvested once: root tubers, stem tubers, leafy crops.

One mechanism, three thin classes:

    RootTuberYieldModel   sweet potato, cassava, ...   (organ: root_tuber)
    StemTuberYieldModel   potato, ...                  (organ: stem_tuber)
    LeafyYieldModel       lettuce, kale, ...           (organ: leaf or stem)

The crop's harvestable_organ says which organ is taken; the class only checks
that it matches the crop type, so a wiring mistake in a plant file fails loudly.

Behaviour:

* Once the crop is old enough (first_harvest_min_days) the standing marketable
  mass of the harvestable organ is reported as harvestable_biomass_g.
* On the harvest day all of it is picked in one go and reported through
  harvested_biomass_g. The engine removes it from the plant and keeps the
  cumulative total. After that the model reports nothing more to harvest.
* The harvest day is the crop's cycle_max_days (its last growth day) unless
  SingleHarvestParameters.harvest_age_days says otherwise. A run that ends
  earlier simply reports the standing mass and no harvest.

Stress effects are OFF by default. With them off, yield is the biomass the growth
model produced, picked once, and no invented numbers reach the results. Switch a
hook on per crop only with a sourced value: heat days above a threshold and low
water-factor days each add a marketable-mass loss (capped), and the lost share
stays on the plant, unharvested.
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


@dataclass(frozen=True)
class SingleHarvestParameters:
    # Age (days, 1-based) of the single harvest. None: the crop's cycle_max_days.
    harvest_age_days: int | None = None

    # ---- optional stress hooks, off while the threshold is None
    heat_threshold_c: float | None = None  # a day above this adds heat_loss_per_day
    heat_loss_per_day: float = 0.0
    water_threshold: float | None = None  # a day with water factor below this adds water_loss_per_day
    water_loss_per_day: float = 0.0
    max_quality_loss: float = 0.5  #  : cap on the total loss; inactive unless a hook is on

    def __post_init__(self) -> None:
        if self.harvest_age_days is not None and (
            int(self.harvest_age_days) != self.harvest_age_days or self.harvest_age_days < 1
        ):
            raise ValueError("harvest_age_days must be a whole number >= 1")
        numbers = (
            self.heat_loss_per_day, self.water_loss_per_day, self.max_quality_loss,
            *(v for v in (self.heat_threshold_c, self.water_threshold) if v is not None),
        )
        if not all(math.isfinite(v) for v in numbers):
            raise ValueError("single-harvest parameters must be finite")
        if self.heat_loss_per_day < 0.0 or self.water_loss_per_day < 0.0:
            raise ValueError("loss per day must not be negative")
        if not 0.0 <= self.max_quality_loss <= 1.0:
            raise ValueError("max_quality_loss must be in [0, 1]")
        if self.water_threshold is not None and not 0.0 < self.water_threshold <= 1.0:
            raise ValueError("water_threshold must be in (0, 1]")

    @property
    def uses_context(self) -> bool:
        return self.heat_threshold_c is not None or self.water_threshold is not None


class SingleHarvestYieldModel(YieldModel):
    # Organs this class accepts as harvestable_organ. None accepts any.
    expected_organs: tuple[str, ...] | None = None

    def __init__(self, parameters: SingleHarvestParameters | None = None) -> None:
        self.parameters = parameters or SingleHarvestParameters()
        self._reset()

    # -- per-run state ------------------------------------------------------ #
    def _reset(self) -> None:
        self._next_day = 0
        self._harvested = False
        self._loss = 0.0
        self._heat_days = 0
        self._water_days = 0

    def initialize(self, crop: CropParameters, greenhouse: GreenhouseConfig) -> None:
        self._reset()

    # -- contract ------------------------------------------------------------ #
    def estimate_yield(
        self,
        crop: CropParameters,
        state: CropState,
        day_index: int,
        context: YieldContext | None = None,
    ) -> YieldState:
        p = self.parameters
        organ = crop.harvestable_organ

        if self.expected_organs is not None and organ not in self.expected_organs:
            raise ValueError(
                f"{type(self).__name__} harvests {self.expected_organs}, but "
                f"{crop.name} has harvestable_organ={organ!r}"
            )
        if p.uses_context and context is None:
            raise ValueError(
                f"{type(self).__name__} has a stress hook on and needs a "
                "YieldContext from the engine"
            )
        if day_index != self._next_day:
            raise ValueError(
                f"days must be requested in order (expected {self._next_day}, "
                f"got {day_index}); call initialize() for a new run"
            )
        self._next_day += 1

        harvest_age = p.harvest_age_days or crop.cycle_max_days
        if harvest_age < crop.first_harvest_min_days:
            raise ValueError(
                f"{crop.name}: harvest age {harvest_age} is before "
                f"first_harvest_min_days={crop.first_harvest_min_days}"
            )

        diagnostics = self._diagnostics
        if self._harvested:
            return YieldState(0.0, False, 0.0, diagnostics())

        # Stress hooks (off unless a threshold is set): accumulate marketable loss.
        if context is not None:
            if (
                p.heat_threshold_c is not None
                and context.environment.temperature_c > p.heat_threshold_c
            ):
                self._heat_days += 1
                self._loss += p.heat_loss_per_day
            if (
                p.water_threshold is not None
                and context.resources.water_factor < p.water_threshold
            ):
                self._water_days += 1
                self._loss += p.water_loss_per_day
            self._loss = min(self._loss, p.max_quality_loss)

        age = day_index + 1
        organ_g = max(0.0, state.biomass_g.get(organ, 0.0))
        ready = age >= crop.first_harvest_min_days
        standing_g = organ_g * (1.0 - self._loss) if ready else 0.0

        harvested_g = 0.0
        if age >= harvest_age and standing_g > 0.0:
            harvested_g = standing_g  # the unmarketable share stays on the plant
            self._harvested = True

        return YieldState(
            harvestable_biomass_g=standing_g,
            yield_ready=standing_g > 0.0,
            harvested_biomass_g=harvested_g,
            diagnostics=diagnostics(),
        )

    def _diagnostics(self) -> dict[str, float]:
        return {
            "quality_loss_fraction": self._loss,
            "heat_stress_days": float(self._heat_days),
            "water_stress_days": float(self._water_days),
        }


class RootTuberYieldModel(SingleHarvestYieldModel):
    """Root tubers (sweet potato, cassava, ...)."""

    expected_organs = ("root_tuber",)


class StemTuberYieldModel(SingleHarvestYieldModel):
    """Stem tubers (potato, ...)."""

    expected_organs = ("stem_tuber",)


class LeafyYieldModel(SingleHarvestYieldModel):
    """Leaf and stem crops (lettuce, kale, ...). One harvestable organ per crop."""

    expected_organs = ("leaf", "stem")