from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Tuple

ORGANS = ("leaf", "stem", "root", "flower", "fruit")


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
    sink_demand: Dict[str, float]
    initial_biomass: Dict[str, float]
    harvestable_organ: str
    cycle_min_days: int
    cycle_max_days: int
    first_harvest_min_days: int
    first_harvest_max_days: int

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

@dataclass(frozen=True)
class EnvironmentConditions:
    temperature_c: float
    light_hours: float
    irradiance_ppfd: float
    airflow_m_s: float


@dataclass(frozen=True)
class ResourceAvailability:
    water_factor: float = 1.0
    nutrient_factor: float = 1.0


@dataclass
class CropState:
    biomass_g: Dict[str, float]
    reserve_g: float = 0.0
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


@dataclass(frozen=True)
class YieldState:
    """Yield estimate; this baseline does not remove harvested biomass from the plant."""
    harvestable_biomass_g: float
    yield_ready: bool