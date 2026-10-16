"""Generic crop-growth fallback used by the initial tomato setup.

Baseline biomass-accounting rules (README, "Core biomass and carbon accounting"):

* Reserves are a per-plant store of assimilates. Leftover assimilates after
  maintenance respiration and growth are stored, and the store is drawn down to
  buffer growth on days when current assimilation cannot meet sink demand.
  Reserves never fall below zero.
* Senescence removes living biomass from an organ and records the same amount in
  a cumulative senesced (litter) pool, so lost biomass is tracked separately
  from living biomass.
* Neither living biomass nor reserves are allowed to become negative, and no
  organ growth is produced when the required assimilates are unavailable.
"""
import math

from data.models.contracts import CropGrowthModel
from data.models.types import (
    CropParameters,
    CropState,
    EnvironmentConditions,
    GrowthFlux,
    ORGANS,
    ResourceAvailability,
)

# TEST VALUE: reserves are capped at this fraction of post-growth living biomass
# so that unused assimilates cannot accumulate without bound.
RESERVE_CAP_FRACTION = 0.10  # TEST VALUE

# TEST VALUE: daily leaf senescence as a fraction of current leaf biomass.
LEAF_SENESCENCE_RATE = 0.005  # TEST VALUE


def temperature_response(temp: float, base: float, optimum: float, maximum: float) -> float:
    """Triangular cardinal-temperature response bounded to [0, 1]."""
    if temp <= base or temp >= maximum:
        return 0.0
    if temp <= optimum:
        return (temp - base) / max(optimum - base, 1e-9)
    return (maximum - temp) / max(maximum - optimum, 1e-9)


class GenericCropGrowthModel(CropGrowthModel):
    """Simple biomass-first fallback, not a calibrated crop-specific model."""

    def initialize(self, crop: CropParameters) -> CropState:
        return CropState(
            biomass_g={organ: float(crop.initial_biomass.get(organ, 0.0)) for organ in ORGANS},
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
        area = max(0.0, 0.25)  # overwritten below from the engine-provided LAI basis
        # The generic model's baseline uses the same per-plant ground area convention
        # as the original prototype. Area scaling is applied by the engine through
        # the temporary `_area_per_plant_m2` attribute when available.
        area = max(float(getattr(state, "_area_per_plant_m2", area)), 1e-9)
        leaf_biomass = max(0.0, state.biomass_g.get("leaf", 0.0))
        lai = leaf_biomass * crop.sla / area
        intercepted_fraction = 1.0 - math.exp(-crop.extinction_k * max(lai, 0.0))

        # Approximate conversion from PPFD to daily PAR energy (MJ/m²/day).
        daily_par_mj_m2 = (
            environment.irradiance_ppfd * environment.light_hours * 3600 / 1_000_000 / 4.57
        )
        f_temp = temperature_response(
            environment.temperature_c, crop.t_base, crop.t_opt, crop.t_max
        )
        f_environment = max(0.0, min(1.0, resources.water_factor)) * max(
            0.0, min(1.0, resources.nutrient_factor)
        )
        gross_assimilation = (
            crop.lue
            * daily_par_mj_m2
            * intercepted_fraction
            * area
            * f_temp
            * f_environment
        )

        # TEST VALUE: Q10=2.0 is a provisional maintenance-respiration assumption.
        q10 = 2.0 ** ((environment.temperature_c - 25.0) / 10.0)
        maintenance_respiration = q10 * sum(
            crop.maintenance.get(organ, 0.0) * max(0.0, state.biomass_g.get(organ, 0.0))
            for organ in ORGANS
        )

        age = state.development_day + 1
        demand = {organ: max(0.0, crop.sink_demand.get(organ, 0.0)) for organ in ORGANS}
        if age < crop.first_harvest_min_days:
            demand["fruit"] = 0.0
            demand["flower"] = min(demand.get("flower", 0.0), 0.01)
        total_demand = sum(demand.values())

        # --- Reserve behavior -------------------------------------------------
        # Carbon available for growth is today's net assimilation plus whatever
        # is already held in the reserve store. Reserves make assimilates from
        # earlier days available again when current assimilation is insufficient.
        net_assimilation = gross_assimilation - maintenance_respiration
        available = max(0.0, state.reserve_g) + net_assimilation
        maintenance_deficit = 0.0
        if available < 0.0:
            # Maintenance respiration exceeded reserves plus assimilation. No
            # carbon remains for growth and the reserve store is emptied, but it
            # is never allowed to go negative.
            maintenance_deficit = -available
            available = 0.0

        if total_demand <= 0.0:
            # No sink is requesting carbon, so whatever is available is stored.
            organ_growth = {organ: 0.0 for organ in ORGANS}
            reserve_after = available
            limiting_factor = "no sink demand"
        elif available >= total_demand:
            # Sink-limited: every organ receives its full demand and the
            # remainder is stored in the reserve pool.
            organ_growth = dict(demand)
            reserve_after = available - total_demand
            limiting_factor = "sink"
        else:
            # Source-limited: assimilates cannot meet demand. Available carbon is
            # shared proportionally and nothing is stored. Growth can never
            # exceed the carbon that is actually available.
            organ_growth = {
                organ: available * demand.get(organ, 0.0) / total_demand for organ in ORGANS
            }
            reserve_after = 0.0
            limiting_factor = "source"

        # --- Senescence -------------------------------------------------------
        # Dying leaf tissue is removed from living biomass and recorded in the
        # cumulative senesced (litter) pool. The engine applies both changes, so
        # lost biomass is tracked separately rather than silently discarded.
        organ_loss = {organ: 0.0 for organ in ORGANS}
        organ_loss["leaf"] = (
            max(0.0, state.biomass_g.get("leaf", 0.0)) * LEAF_SENESCENCE_RATE
        )

        # --- Reserve storage cap ---------------------------------------------
        # Bound the reserve store so unused assimilates cannot accumulate without
        # limit. Carbon above the cap is not carried forward.
        estimated_post_growth = sum(state.biomass_g.values()) + sum(organ_growth.values())
        reserve_cap = RESERVE_CAP_FRACTION * max(0.0, estimated_post_growth)
        reserve_after = min(max(0.0, reserve_after), reserve_cap)

        return GrowthFlux(
            organ_growth_g=organ_growth,
            organ_loss_g=organ_loss,
            reserve_after_g=reserve_after,
            lai=lai,
            gross_assimilation_g_day=gross_assimilation,
            maintenance_respiration_g_day=maintenance_respiration,
            sink_demand_g_day=total_demand,
            limiting_factor=limiting_factor,
            temperature_factor=f_temp,
            environment_factor=f_environment,
            maintenance_deficit_g_day=maintenance_deficit,
        )