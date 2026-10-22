"""Contracts for interchangeable greenhouse crop models."""
from abc import ABC, abstractmethod
from data.models.types import (
    CropParameters,
    CropState,
    EnvironmentConditions,
    GreenhouseConfig,
    GrowthFlux,
    ResourceAvailability,
    YieldState,
    YieldContext
)
class EnvironmentModel(ABC):
    @abstractmethod
    def conditions_for_day(
        self, greenhouse: GreenhouseConfig, day_index: int
    ) -> EnvironmentConditions:
        """Return environmental conditionals for a simulation time step"""

class CropGrowthModel(ABC):
    @abstractmethod
    def initialize(self, crop: CropParameters) -> CropState:
        """Create the initial dynamic state for a crop."""

    @abstractmethod
    def calculate_growth(
        self,
        crop: CropParameters,
        state: CropState,
        environment: EnvironmentConditions,
        resources: ResourceAvailability,
    ) -> GrowthFlux:
        """Calculate one time step of growth without mutating the supplied state."""
class SoilFertilizerModel(ABC):
    @abstractmethod
    def initialize(self, greenhouse: GreenhouseConfig) -> None:
        """Initialize any model state needed for soil, water, or fertilizer."""

    @abstractmethod
    def resources_for_day(
        self,
        crop: CropParameters,
        greenhouse: GreenhouseConfig,
        day_index: int,
    ) -> ResourceAvailability:
        """Return water and nutrient availability factors for this time step."""

class YieldModel(ABC):
    def initialize(
        self, crop: CropParameters, greenhouse: GreenhouseConfig
    ) -> None:
        """Reset any per-run state (stress counters, fruit-set history, ...).
 
        Optional. The engine calls this once at the start of every run, before
        the first ``estimate_yield``. A stateless model can ignore it.
        """
 
    @abstractmethod
    def estimate_yield(
        self,
        crop: CropParameters,
        state: CropState,
        day_index: int,
        context: YieldContext | None = None,
    ) -> YieldState:
        """Estimate harvestable output from the current crop state.
 
        The engine calls this exactly once per simulated day, in order, after
        the day's growth has been applied to ``state``. Do not mutate ``state``.
 
        ``context`` carries the day's environment, water and nutrient
        availability, growth fluxes, soil state and the engine's growth
        decision, so yield can respond to stress and not only to biomass.
        The engine always supplies it. It defaults to None only so older
        callers and tests that pass three arguments keep working; a model that
        needs the context should raise a clear error when it is missing.
 
        Models that keep running totals should keep them on the model object
        (reset in ``initialize``) and report them through
        ``YieldState.diagnostics`` so they appear in the output.
        """
 

