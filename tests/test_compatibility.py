"""Component-level tests: each part is exercised without building the others."""
from types import SimpleNamespace

import pytest

from data.models.soil import (
    DemandLedger,
    IrrigationSchedule,
    NutrientApplication,
    NutrientPools,
    SoilProfile,
    TextureSoilFertilizerModel,
    WaterBalance,
    WaterFlux,
)

GREENHOUSE = SimpleNamespace(water_factor=1.0, nutrient_factor=1.0)


def crop(name="tomato", water=1.0, nutrient=1.0, area=1.0):
    return SimpleNamespace(
        name=name, water_demand_coefficient=water, nutrient_demand_coefficient=nutrient, area_fraction=area
    )


# -- SoilProfile ------------------------------------------------------------ #
def test_profile_class_average_and_validation():
    p = SoilProfile.build("clay", "class_average")
    assert (p.hydraulics.wilting_point, p.hydraulics.field_capacity, p.hydraulics.saturation) == (0.272, 0.396, 0.475)
    with pytest.raises(ValueError):
        SoilProfile.build("loam", "made_up")
    with pytest.raises(ValueError):
        SoilProfile.build("peat")


# -- WaterBalance (no nutrients, no crops) ---------------------------------- #
def test_water_balance_uptake_and_flux():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0))
    wb.open_day(0)
    assert wb.factor() == 1.0
    flux = wb.close_day(10.0)
    assert flux.uptake_mm == pytest.approx(10.0)
    assert flux.drained_mm == 0.0
    assert flux.field_capacity_mm == pytest.approx(wb.field_capacity_mm)
    assert wb.factor() < 1.0


def test_water_balance_runoff_and_drainage_from_big_irrigation():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=1000.0))
    wb.open_day(0)
    cum = wb.cumulative()
    assert cum["runoff_mm"] > 0.0
    assert wb.gravitational_mm == pytest.approx(wb.gravitational_capacity_mm)
    flux = wb.close_day(0.0)
    assert flux.drained_mm == pytest.approx(wb.gravitational_capacity_mm)
    assert wb.gravitational_mm == 0.0


def test_water_balance_validation_and_reset():
    with pytest.raises(ValueError):
        WaterBalance(SoilProfile.build("loam"), root_zone_depth_m=0.0)
    with pytest.raises(ValueError):
        WaterBalance(SoilProfile.build("loam"), depletion_fraction=1.0)
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0))
    wb.open_day(0)
    wb.close_day(20.0)
    wb.reset()
    assert wb.factor() == 1.0 and wb.cumulative()["water_uptake_mm"] == 0.0


def test_water_flux_washout_fraction():
    assert WaterFlux(0.0, 0.0, 100.0).washout_fraction == 0.0
    assert 0.0 < WaterFlux(0.0, 50.0, 100.0).washout_fraction < 1.0
    assert WaterFlux(0.0, 50.0, 0.0).washout_fraction == 0.0


# -- NutrientPools (fed a hand-made WaterFlux, no soil) ---------------------- #
def test_pools_only_mobile_nutrients_leach():
    pools = NutrientPools(NutrientApplication(100, 60, 60))
    pools.open_day(0)
    pools.close_day((1.0, 1.0, 1.0), WaterFlux(0.0, 100.0, 200.0))
    levels = pools.levels()
    assert levels["n"] < 99.0
    assert levels["p2o5"] == pytest.approx(59.0) and levels["k2o"] == pytest.approx(59.0)
    cum = pools.cumulative()
    assert cum["n_leached"] > 0.0 and cum["p2o5_leached"] == 0.0


def test_pools_factor_drops_to_zero_when_pool_is_empty():
    pools = NutrientPools(NutrientApplication(10, 10, 10))
    pools.open_day(0)
    assert pools.factor() == 1.0  # first day: no previous demand yet
    pools.close_day((1000.0, 1000.0, 1000.0), WaterFlux(0.0, 0.0, 100.0))
    assert pools.factor() == 0.0


def test_pools_schedule_and_validation():
    pools = NutrientPools(NutrientApplication(100, 0, 0, schedule=((0, 0.5), (5, 0.5))))
    pools.open_day(0)
    assert pools.levels()["n"] == pytest.approx(50.0)
    pools.open_day(5)
    assert pools.levels()["n"] == pytest.approx(100.0)
    with pytest.raises(ValueError):
        NutrientPools(NutrientApplication(), combination="sum")


# -- DemandLedger ------------------------------------------------------------ #
def test_ledger_register_weight_record_and_close():
    ledger = DemandLedger(reference_demand_mm_day=4.0, season_days=90, recommended_npk={"tomato": (90.0, 45.0, 45.0)})
    ledger.register(crop("tomato", area=0.5))
    ledger.register(crop("tomato", area=0.5))  # same day: first entry kept
    ledger.record_uptake("tomato", water_mm=7.0, n_kg_ha=2.0)
    total = ledger.close_day()
    assert total.water_mm == pytest.approx(7.0)
    assert total.npk_kg_ha == pytest.approx((2.0, 0.25, 0.25))
    assert ledger.close_day().water_mm == 0.0  # cleared
    with pytest.raises(KeyError):
        ledger.record_uptake("tomato", water_mm=1.0)


def test_ledger_validation():
    with pytest.raises(ValueError):
        DemandLedger(season_days=0)
    with pytest.raises(ValueError):
        DemandLedger(reference_demand_mm_day=-1.0)


# -- Facade wiring ------------------------------------------------------------ #
def test_from_components_lets_you_swap_the_nutrient_part():
    class FixedNutrients:
        def reset(self): pass
        def open_day(self, day): pass
        def close_day(self, demand_npk, flux): self.last_flux = flux
        def factor(self): return 0.25

    stub = FixedNutrients()
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0))
    m = TextureSoilFertilizerModel.from_components(wb, stub)
    values = [m.resources_for_day(crop(), GREENHOUSE, d) for d in range(3)]
    assert all(v.nutrient_factor == 0.25 for v in values)
    assert values[0].water_factor == 1.0 and values[2].water_factor < 1.0
    assert isinstance(stub.last_flux, WaterFlux) and stub.last_flux.uptake_mm > 0.0


def test_facade_passes_water_flux_to_nutrients_in_order():
    m = TextureSoilFertilizerModel("sandy_loam", nutrients=NutrientApplication(100, 60, 60),
                                   irrigation=IrrigationSchedule(amount_mm=60.0), root_zone_depth_m=0.6)
    for d in range(5):
        m.resources_for_day(crop(), GREENHOUSE, d)
    s = m.snapshot()
    assert s["cum_drained_mm"] > 0.0 and s["cum_n_leached"] > 0.0
    assert m.nutrient_pools.cumulative()["n_leached"] == s["cum_n_leached"]
    assert m.water_balance.cumulative()["drained_mm"] == s["cum_drained_mm"]


def test_ledger_uses_the_crops_growth_days_and_falls_back_otherwise():
    ledger = DemandLedger(season_days=90, recommended_npk={"tomato": (60.0, 30.0, 30.0)})
    c = crop("tomato")
    c.growth_days = 30
    ledger.register(c)
    assert ledger.close_day().npk_kg_ha == pytest.approx((2.0, 1.0, 1.0))
    ledger.register(crop("tomato"))  # no growth_days attribute -> constructor fallback
    assert ledger.close_day().npk_kg_ha == pytest.approx((60.0 / 90, 30.0 / 90, 30.0 / 90))