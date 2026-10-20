"""Contracts for interchangeable greenhouse crop models."""
from abc import ABC, abstractmethod
from data.models.types import (
    CropParameters,
    CropState,
    EnvironmentConditions,
    GreenhouseConfig,
    GrowthFlux,
    ResourceAvailability,
    YieldState
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
    @abstractmethod
    def estimate_yield(
        self, crop: CropParameters, state: CropState, day_index: int
    ) -> YieldState:
        """Estimate harvestable output from the current crop state."""
