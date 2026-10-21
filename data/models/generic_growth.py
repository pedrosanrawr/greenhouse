"""Generic crop-growth model using the shared light module."""
import math

from data.models.contracts import CropGrowthModel
from data.models.light import calculate_light
from data.models.types import (
    CropParameters,
    CropState,
    EnvironmentConditions,
    GrowthFlux,
    ORGANS,
    ResourceAvailability,
)

from data.models.air import (
    airflow_response_factor,
    calculate_air_diagnostics,
    co2_response_factor,
    vpd_response_factor,
)

# Provisional assumptions retained from the existing growth model.
RESERVE_CAP_FRACTION = 0.10
LEAF_SENESCENCE_RATE = 0.005


def temperature_response(
    temp: float,
    base: float,
    optimum: float,
    maximum: float,
) -> float:
    """Triangular temperature-response factor bounded to [0, 1]."""
    if temp <= base or temp >= maximum:
        return 0.0

    if temp <= optimum:
        return (temp - base) / max(optimum - base, 1e-9)

    return (maximum - temp) / max(maximum - optimum, 1e-9)


class GenericCropGrowthModel(CropGrowthModel):
    """Simple biomass-first fallback, not a calibrated crop-specific model."""

    def initialize(self, crop: CropParameters) -> CropState:
        return CropState(
            biomass_g={
                organ: float(crop.initial_biomass.get(organ, 0.0))
                for organ in ORGANS
            },
            reserve_g=0.0,
            senesced_biomass_g=0.0,
            development_day=0,
        )

    def calculate_growth(
        self,
        crop: CropParameters,
        state: CropState,
        environment: EnvironmentConditions,
        resources: ResourceAvailability,
    ) -> GrowthFlux:
        # Ground area allocated to one plant.
        area = max(
            float(getattr(state, "_area_per_plant_m2", 0.25)),
            1e-9,
        )

        leaf_biomass = max(
            0.0,
            state.biomass_g.get("leaf", 0.0),
        )

        # Light module handles PAR conversion, cover transmission,
        # leaf area index, and canopy interception.
        light = calculate_light(
            solar_radiation_mj_m2_day=(
                environment.solar_radiation_mj_m2_day
            ),
            leaf_biomass_g=leaf_biomass,
            sla_m2_g=crop.sla,
            extinction_k=crop.extinction_k,
            area_per_plant_m2=area,
            cover_par_transmittance=(
                environment.cover_par_transmittance
            ),
        )

        lai = light.lai

        # Crop temperature response.
        f_temp = temperature_response(
            environment.temperature_c,
            crop.t_base,
            crop.t_opt,
            crop.t_max,
        )

        # Atmospheric diagnostics
        air = calculate_air_diagnostics(
            temperature_c=environment.temperature_c,
            co2_ppm=environment.co2_ppm,
            relative_humidity_pct=environment.relative_humidity_pct,
            airflow_m_s=environment.airflow_m_s,
        )

        # CO2: inactive unless a crop-specific parameter is supplied.
        co2_active = crop.co2_k_half_ppm is not None

        f_co2 = (
            co2_response_factor(
                co2_ppm=air.co2_ppm,
                k_half_ppm=crop.co2_k_half_ppm,
            )
            if co2_active
            else 1.0
        )

        # VPD: inactive unless all crop-specific thresholds are supplied.
        vpd_active = crop.vpd_low_kpa is not None

        f_vpd = vpd_response_factor(
            vpd_kpa=air.vpd_kpa,
            low_kpa=crop.vpd_low_kpa,
            high_kpa=crop.vpd_high_kpa,
            min_factor=crop.vpd_min_factor,
        )

        # Airflow: inactive unless its crop-specific parameters are supplied.
        airflow_active = crop.airflow_sensitivity is not None

        f_airflow = airflow_response_factor(
            airflow_m_s=air.airflow_m_s,
            sensitivity=crop.airflow_sensitivity,
            half_saturation_m_s=crop.airflow_half_saturation_m_s,
        )

        # Water and nutrient limitation.
        water_factor = max(
            0.0,
            min(1.0, resources.water_factor),
        )
        nutrient_factor = max(
            0.0,
            min(1.0, resources.nutrient_factor),
        )
        f_environment = water_factor * nutrient_factor

        # RUE/LUE converts intercepted PAR into biomass-equivalent
        # assimilate. IPAR is per m² ground, so multiply by the
        # plant's allocated ground area exactly once.
        gross_assimilation = (
            crop.lue
            * light.ipar_mj_m2_day
            * area
            * f_temp
            * f_environment
            * f_co2
            * f_vpd
            * f_airflow
        )

        # Existing provisional maintenance-respiration model.
        # Retained temporarily for compatibility with the current engine.
        q10 = 2.0 ** (
            (environment.temperature_c - 25.0) / 10.0
        )

        maintenance_respiration = q10 * sum(
            crop.maintenance.get(organ, 0.0)
            * max(0.0, state.biomass_g.get(organ, 0.0))
            for organ in ORGANS
        )

        # Existing provisional organ-demand model.
        age = state.development_day + 1
        demand = {
            organ: max(
                0.0,
                crop.sink_demand.get(organ, 0.0),
            )
            for organ in ORGANS
        }

        if age < crop.first_harvest_min_days:
            demand["fruit"] = 0.0
            demand["flower"] = min(
                demand.get("flower", 0.0),
                0.01,
            )

        total_demand = sum(demand.values())

        # Legacy reserve/accounting behavior retained because the
        # current engine and GrowthFlux interface still expect it.
        net_assimilation = (
            gross_assimilation - maintenance_respiration
        )
        available = max(0.0, state.reserve_g) + net_assimilation

        maintenance_deficit = 0.0

        if available < 0.0:
            maintenance_deficit = -available
            available = 0.0

        if total_demand <= 0.0:
            organ_growth = {
                organ: 0.0 for organ in ORGANS
            }
            reserve_after = available
            limiting_factor = "no sink demand"

        elif available >= total_demand:
            organ_growth = dict(demand)
            reserve_after = available - total_demand
            limiting_factor = "sink"

        else:
            organ_growth = {
                organ: (
                    available * demand.get(organ, 0.0)
                    / total_demand
                )
                for organ in ORGANS
            }
            reserve_after = 0.0
            limiting_factor = "source"

        # Track leaf senescence as an explicit biomass loss.
        organ_loss = {
            organ: 0.0 for organ in ORGANS
        }
        organ_loss["leaf"] = (
            max(
                0.0,
                state.biomass_g.get("leaf", 0.0),
            )
            * LEAF_SENESCENCE_RATE
        )

        # Provisional reserve cap.
        estimated_post_growth = (
            sum(state.biomass_g.values())
            + sum(organ_growth.values())
        )
        reserve_cap = (
            RESERVE_CAP_FRACTION
            * max(0.0, estimated_post_growth)
        )
        reserve_after = min(
            max(0.0, reserve_after),
            reserve_cap,
        )

        return GrowthFlux(
            organ_growth_g=organ_growth,
            organ_loss_g=organ_loss,
            reserve_after_g=reserve_after,
            lai=lai,
            gross_assimilation_g_day=gross_assimilation,
            maintenance_respiration_g_day=(
                maintenance_respiration
            ),
            sink_demand_g_day=total_demand,
            limiting_factor=limiting_factor,
            temperature_factor=f_temp,
            environment_factor=f_environment,
            maintenance_deficit_g_day=maintenance_deficit,
            vpd_kpa=air.vpd_kpa,
            co2_factor=f_co2,
            vpd_factor=f_vpd,
            airflow_factor=f_airflow,
            co2_response_active=co2_active,
            vpd_response_active=vpd_active,
            airflow_response_active=airflow_active,
        )