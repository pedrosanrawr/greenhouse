"""Comprehensive component and integration tests for Greenlab's soil model.

Add this beside your existing tests/test_soil.py, then run from the repository root with:
    python -m pytest tests/test_soil.py tests/test_soil_comprehensive.py -v

These tests check implementation consistency, not agronomic calibration. Several
soil-water and nutrient parameters in the model are explicitly provisional.
"""
from types import SimpleNamespace
import math
import warnings

import pytest

from data.models.soil import (
    DEFAULT_RECOMMENDED_NPK,
    DemandLedger,
    IrrigationSchedule,
    NutrientApplication,
    NutrientPools,
    SoilProfile,
    SoilTexture,
    TextureSoilFertilizerModel,
    WaterBalance,
    WaterFlux,
    clamp01,
    get_texture,
    saxton_rawls_hydraulics,
)


GREENHOUSE = SimpleNamespace(water_factor=1.0, nutrient_factor=1.0)


def crop(name="tomato", water=1.0, nutrient=1.0, area=1.0, growth_days=None):
    """Minimal crop-shaped object accepted by DemandLedger and soil facade."""
    result = SimpleNamespace(
        name=name,
        water_demand_coefficient=water,
        nutrient_demand_coefficient=nutrient,
        area_fraction=area,
    )
    if growth_days is not None:
        result.growth_days = growth_days
    return result


def no_drainage_flux():
    return WaterFlux(uptake_mm=0.0, drained_mm=0.0, field_capacity_mm=100.0)


# ---------------------------------------------------------------------------
# Helpers and soil profile / hydraulic properties
# ---------------------------------------------------------------------------


def test_clamp01_handles_boundaries_and_out_of_range_values():
    assert clamp01(0.0) == 0.0
    assert clamp01(1.0) == 1.0
    assert clamp01(-0.2) == 0.0
    assert clamp01(1.7) == 1.0
    assert clamp01(0.35) == pytest.approx(0.35)


@pytest.mark.parametrize(
    ("label", "expected_name"),
    [
        ("clay", "Clay"),
        ("clay loam", "Clay loam"),
        ("clay-loam", "Clay loam"),
        ("clay_loam", "Clay loam"),
        ("loam", "Loam"),
        ("sandy loam", "Sandy loam"),
        ("sandy-loam", "Sandy loam"),
    ],
)
def test_texture_presets_and_aliases(label, expected_name):
    assert get_texture(label).name == expected_name


def test_get_texture_accepts_a_custom_texture_object_unchanged():
    custom = SoilTexture("custom mix", sand=0.45, clay=0.25, organic_matter_pct=3.0)
    assert get_texture(custom) is custom


def test_unknown_texture_is_rejected():
    with pytest.raises(ValueError, match="Unknown soil"):
        get_texture("peat")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "bad sand", "sand": -0.01, "clay": 0.2},
        {"name": "bad sand", "sand": 1.01, "clay": 0.0},
        {"name": "bad clay", "sand": 0.2, "clay": -0.01},
        {"name": "too much mineral", "sand": 0.7, "clay": 0.4},
        {"name": "negative OM", "sand": 0.4, "clay": 0.2, "organic_matter_pct": -1.0},
    ],
)
def test_soil_texture_rejects_invalid_fractions_and_organic_matter(kwargs):
    with pytest.raises(ValueError):
        SoilTexture(**kwargs)


def test_saxton_rawls_hydraulics_has_ordered_water_contents_for_presets():
    for texture in ("clay", "clay_loam", "loam", "sandy_loam"):
        h = SoilProfile.build(texture).hydraulics
        assert 0.0 < h.wilting_point < h.field_capacity < h.saturation < 1.0
        assert h.plant_available_water == pytest.approx(h.field_capacity - h.wilting_point)
        assert h.b > 0.0
        assert h.lambda_ == pytest.approx(1.0 / h.b)
        assert h.ksat_mm_h > 0.0
        assert h.bulk_density > 0.0


def test_saxton_rawls_warns_outside_published_input_range():
    with pytest.warns(UserWarning, match="outside the Saxton"):
        saxton_rawls_hydraulics(sand=0.1, clay=0.65, organic_matter_pct=9.0)


def test_profile_class_average_matches_configured_reference_values():
    profile = SoilProfile.build("clay", hydraulic_source="class_average")
    h = profile.hydraulics
    assert h.wilting_point == pytest.approx(0.272)
    assert h.field_capacity == pytest.approx(0.396)
    assert h.saturation == pytest.approx(0.475)
    assert h.plant_available_water == pytest.approx(0.124)


def test_profile_rejects_invalid_hydraulic_source_and_missing_class_average():
    with pytest.raises(ValueError, match="hydraulic_source"):
        SoilProfile.build("loam", hydraulic_source="made_up")

    custom = SoilTexture("custom", sand=0.45, clay=0.25)
    with pytest.raises(ValueError, match="no class-average"):
        SoilProfile.build(custom, hydraulic_source="class_average")


# ---------------------------------------------------------------------------
# Irrigation schedule and water-flux diagnostics
# ---------------------------------------------------------------------------


def test_irrigation_schedule_events_respect_interval_and_start_day():
    schedule = IrrigationSchedule(interval_days=3, amount_mm=12.0, start_day=2)
    assert [day for day in range(9) if schedule.event_on(day)] == [2, 5, 8]


def test_irrigation_schedule_rejects_invalid_values():
    with pytest.raises(ValueError, match="invalid irrigation"):
        IrrigationSchedule(interval_days=0, amount_mm=12.0)
    with pytest.raises(ValueError, match="invalid irrigation"):
        IrrigationSchedule(interval_days=1, amount_mm=-1.0)
    with pytest.raises(ValueError, match="invalid irrigation"):
        IrrigationSchedule(interval_days=1, amount_mm=1.0, start_day=-1)


def test_water_flux_washout_fraction_is_bounded_and_uses_field_capacity():
    assert WaterFlux(0.0, 0.0, 100.0).washout_fraction == pytest.approx(0.0)
    flux = WaterFlux(0.0, 50.0, 100.0)
    assert flux.washout_fraction == pytest.approx(1.0 - math.exp(-0.5))
    assert 0.0 < flux.washout_fraction < 1.0
    assert WaterFlux(0.0, 50.0, 0.0).washout_fraction == 0.0


# ---------------------------------------------------------------------------
# Root-zone water balance
# ---------------------------------------------------------------------------


def test_water_balance_initializes_available_water_from_taw_fraction():
    full = WaterBalance(SoilProfile.build("loam"), initial_water_fraction=1.0)
    half = WaterBalance(SoilProfile.build("loam"), initial_water_fraction=0.5)
    dry = WaterBalance(SoilProfile.build("loam"), initial_water_fraction=0.0)
    assert full.available_water_mm == pytest.approx(full.taw_mm)
    assert half.available_water_mm == pytest.approx(0.5 * half.taw_mm)
    assert dry.available_water_mm == pytest.approx(0.0)
    assert dry.factor() == 0.0


def test_initial_water_fraction_is_clamped_to_zero_through_one():
    too_dry = WaterBalance(SoilProfile.build("loam"), initial_water_fraction=-2.0)
    too_wet = WaterBalance(SoilProfile.build("loam"), initial_water_fraction=2.0)
    assert too_dry.available_water_mm == pytest.approx(0.0)
    assert too_wet.available_water_mm == pytest.approx(too_wet.taw_mm)


def test_water_balance_rejects_invalid_root_zone_and_depletion_fraction():
    profile = SoilProfile.build("loam")
    with pytest.raises(ValueError, match="root zone depth"):
        WaterBalance(profile, root_zone_depth_m=0.0)
    with pytest.raises(ValueError, match="root zone depth"):
        WaterBalance(profile, root_zone_depth_m=-0.1)
    with pytest.raises(ValueError, match="depletion_fraction"):
        WaterBalance(profile, depletion_fraction=1.0)
    with pytest.raises(ValueError, match="depletion_fraction"):
        WaterBalance(profile, depletion_fraction=-0.1)


def test_water_uptake_reduces_available_water_and_water_factor():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0))
    initial = wb.available_water_mm
    wb.open_day(0)
    assert wb.factor() == pytest.approx(1.0)
    flux = wb.close_day(10.0)
    assert flux.uptake_mm == pytest.approx(10.0)
    assert flux.drained_mm == pytest.approx(0.0)
    assert flux.field_capacity_mm == pytest.approx(wb.field_capacity_mm)
    assert wb.available_water_mm == pytest.approx(initial - 10.0)
    assert wb.factor() < 1.0
    assert wb.cumulative()["water_uptake_mm"] == pytest.approx(10.0)


def test_water_uptake_cannot_exceed_water_remaining():
    wb = WaterBalance(
        SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0), initial_water_fraction=0.25
    )
    available = wb.available_water_mm
    wb.open_day(0)
    flux = wb.close_day(1e9)
    assert flux.uptake_mm == pytest.approx(available)
    assert wb.available_water_mm == pytest.approx(0.0)
    assert wb.factor() == pytest.approx(0.0)


def test_irrigation_refills_water_and_is_recorded_cumulatively():
    schedule = IrrigationSchedule(interval_days=3, amount_mm=12.0, start_day=1)
    wb = WaterBalance(SoilProfile.build("loam"), schedule, initial_water_fraction=0.0)
    wb.open_day(0)
    assert wb.available_water_mm == 0.0
    wb.open_day(1)
    assert wb.available_water_mm == pytest.approx(12.0)
    assert wb.cumulative()["irrigation_mm"] == pytest.approx(12.0)
    wb.open_day(4)
    assert wb.cumulative()["irrigation_mm"] == pytest.approx(24.0)


def test_excess_irrigation_becomes_gravitational_water_then_drainage_and_runoff():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=1000.0))
    wb.open_day(0)
    assert wb.available_water_mm == pytest.approx(wb.taw_mm)
    assert wb.gravitational_mm == pytest.approx(wb.gravitational_capacity_mm)
    assert wb.cumulative()["runoff_mm"] > 0.0
    flux = wb.close_day(0.0)
    assert flux.drained_mm == pytest.approx(wb.gravitational_capacity_mm)
    assert wb.gravitational_mm == pytest.approx(0.0)
    assert wb.cumulative()["drained_mm"] == pytest.approx(flux.drained_mm)


def test_water_factor_never_leaves_zero_to_one_range_under_normal_demand():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=0.0))
    for day in range(20):
        wb.open_day(day)
        wb.close_day(4.0)
        assert 0.0 <= wb.factor() <= 1.0


def test_depletion_fraction_changes_the_water_limitation_threshold():
    strict = WaterBalance(SoilProfile.build("loam"), depletion_fraction=0.0)
    tolerant = WaterBalance(SoilProfile.build("loam"), depletion_fraction=0.5)
    for wb in (strict, tolerant):
        wb.open_day(0)
        wb.close_day(0.6 * wb.taw_mm)
    assert tolerant.factor() > strict.factor()


def test_water_balance_reset_restores_initial_state_and_counters():
    wb = WaterBalance(SoilProfile.build("loam"), IrrigationSchedule(amount_mm=12.0))
    wb.open_day(0)
    wb.close_day(5.0)
    wb.reset()
    assert wb.available_water_mm == pytest.approx(wb.taw_mm)
    assert wb.gravitational_mm == pytest.approx(0.0)
    assert wb.factor() == pytest.approx(1.0)
    assert all(value == 0.0 for value in wb.cumulative().values())


# ---------------------------------------------------------------------------
# Fertilizer application and nutrient pools
# ---------------------------------------------------------------------------


def test_nutrient_application_amounts_schedule_and_tuple():
    application = NutrientApplication(100.0, 60.0, 40.0, schedule=((0, 0.25), (10, 0.75)))
    assert application.as_tuple() == (100.0, 60.0, 40.0)
    assert sum(fraction for _, fraction in application.schedule) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "application",
    [
        {"n_kg_ha": -1.0},
        {"p2o5_kg_ha": -1.0},
        {"k2o_kg_ha": -1.0},
        {"schedule": ()},
        {"schedule": ((-1, 1.0),)},
        {"schedule": ((0, -0.1), (1, 1.1))},
        {"schedule": ((0, 0.5),)},
    ],
)
def test_nutrient_application_rejects_negative_values_and_invalid_schedules(application):
    with pytest.raises(ValueError):
        NutrientApplication(**application)


def test_pools_receive_scheduled_fertilizer_on_the_specified_days():
    pools = NutrientPools(
        NutrientApplication(100.0, 60.0, 40.0, schedule=((0, 0.5), (5, 0.5)))
    )
    pools.open_day(0)
    assert pools.levels()["n"] == pytest.approx(50.0)
    assert pools.cumulative()["n_applied"] == pytest.approx(50.0)
    pools.open_day(5)
    assert pools.levels()["n"] == pytest.approx(100.0)
    assert pools.levels()["p2o5"] == pytest.approx(60.0)
    assert pools.levels()["k2o"] == pytest.approx(40.0)
    assert pools.cumulative()["n_applied"] == pytest.approx(100.0)


def test_pools_only_leach_mobile_nutrients_by_default():
    pools = NutrientPools(NutrientApplication(100.0, 60.0, 60.0))
    pools.open_day(0)
    pools.close_day((1.0, 1.0, 1.0), WaterFlux(0.0, 100.0, 200.0))
    levels = pools.levels()
    assert levels["n"] < 99.0  # uptake plus nitrogen leaching
    assert levels["p2o5"] == pytest.approx(59.0)
    assert levels["k2o"] == pytest.approx(59.0)
    cumulative = pools.cumulative()
    assert cumulative["n_leached"] > 0.0
    assert cumulative["p2o5_leached"] == pytest.approx(0.0)
    assert cumulative["k2o_leached"] == pytest.approx(0.0)


def test_nutrient_uptake_is_limited_by_pool_size():
    pools = NutrientPools(NutrientApplication(10.0, 5.0, 5.0))
    pools.open_day(0)
    pools.close_day((100.0, 1.0, 2.0), no_drainage_flux())
    assert pools.levels()["n"] == pytest.approx(0.0)
    assert pools.levels()["p2o5"] == pytest.approx(4.0)
    assert pools.levels()["k2o"] == pytest.approx(3.0)
    cumulative = pools.cumulative()
    assert cumulative["n_uptake"] == pytest.approx(10.0)
    assert cumulative["p2o5_uptake"] == pytest.approx(1.0)
    assert cumulative["k2o_uptake"] == pytest.approx(2.0)


def test_nutrient_factor_drops_to_zero_when_a_tracked_pool_is_empty():
    pools = NutrientPools(NutrientApplication(10.0, 10.0, 10.0))
    pools.open_day(0)
    assert pools.factor() == pytest.approx(1.0)  # no prior demand on the first day
    pools.close_day((1000.0, 1000.0, 1000.0), no_drainage_flux())
    assert pools.factor() == pytest.approx(0.0)


def test_nutrient_factor_is_one_when_no_nutrients_are_tracked():
    pools = NutrientPools(NutrientApplication(), tracked=())
    pools.open_day(0)
    pools.close_day((100.0, 100.0, 100.0), no_drainage_flux())
    assert pools.factor() == pytest.approx(1.0)


def test_untracked_nutrients_do_not_limit_tracked_nutrients():
    pools = NutrientPools(
        NutrientApplication(),
        indigenous_npk_kg_ha=(5.0, 0.0, 0.0),
        tracked=("n",),
    )
    pools.open_day(0)
    pools.close_day((1.0, 100.0, 100.0), no_drainage_flux())
    assert pools.factor() == pytest.approx(1.0)


def test_nutrient_combination_min_and_product():
    application = NutrientApplication()
    indigenous = (15.0, 30.0, 20.0)
    demand = (10.0, 20.0, 10.0)
    minimum = NutrientPools(application, indigenous, combination="min")
    product = NutrientPools(application, indigenous, combination="product")
    for pools in (minimum, product):
        pools.open_day(0)
        pools.close_day(demand, no_drainage_flux())
    assert minimum.factor() == pytest.approx(0.5)
    assert product.factor() == pytest.approx(0.25)


def test_nutrient_pool_rejects_unknown_tracked_nutrient_and_combination():
    with pytest.raises(ValueError, match="nutrient_combination"):
        NutrientPools(NutrientApplication(), combination="sum")
    with pytest.raises(ValueError, match="unknown nutrient"):
        NutrientPools(NutrientApplication(), tracked=("n", "magnesium"))


def test_custom_leaching_mobility_is_clamped_and_applied():
    pools = NutrientPools(
        NutrientApplication(100.0, 100.0, 100.0),
        leaching_mobility={"n": 2.0, "p2o5": -1.0, "k2o": 1.0},
    )
    assert pools.leaching_mobility == {"n": 1.0, "p2o5": 0.0, "k2o": 1.0}
    pools.open_day(0)
    pools.close_day((0.0, 0.0, 0.0), WaterFlux(0.0, 100.0, 100.0))
    assert pools.cumulative()["n_leached"] > 0.0
    assert pools.cumulative()["p2o5_leached"] == pytest.approx(0.0)
    assert pools.cumulative()["k2o_leached"] > 0.0


def test_nutrient_pool_reset_restores_indigenous_pools_and_counters():
    pools = NutrientPools(
        NutrientApplication(100.0, 50.0, 25.0), indigenous_npk_kg_ha=(2.0, 3.0, 4.0)
    )
    pools.open_day(0)
    pools.close_day((1.0, 1.0, 1.0), no_drainage_flux())
    pools.reset()
    assert pools.levels() == {"n": 2.0, "p2o5": 3.0, "k2o": 4.0}
    assert all(value == 0.0 for value in pools.cumulative().values())


# ---------------------------------------------------------------------------
# Per-crop daily demand ledger
# ---------------------------------------------------------------------------


def test_ledger_sums_different_crop_demands_and_uses_area_weights():
    ledger = DemandLedger(reference_demand_mm_day=4.0, season_days=90,
                          recommended_npk={"tomato": (90.0, 45.0, 45.0), "pepper": (45.0, 45.0, 45.0)})
    ledger.register(crop("tomato", water=1.0, nutrient=1.0, area=0.5))
    ledger.register(crop("pepper", water=0.5, nutrient=1.0, area=0.25))
    total = ledger.close_day()
    assert total.water_mm == pytest.approx(4.0 * 1.0 * 0.5 + 4.0 * 0.5 * 0.25)
    expected_n = 0.5 * 90.0 / 90 + 0.25 * 45.0 / 90
    expected_p = 0.5 * 45.0 / 90 + 0.25 * 45.0 / 90
    assert total.npk_kg_ha == pytest.approx((expected_n, expected_p, expected_p))


def test_ledger_registration_is_case_insensitive_and_duplicate_keeps_first_entry():
    ledger = DemandLedger(recommended_npk={"tomato": (90.0, 45.0, 45.0)})
    ledger.register(crop(" Tomato ", water=1.0, area=0.5))
    ledger.register(crop("tomato", water=9.0, area=1.0))
    total = ledger.close_day()
    assert total.water_mm == pytest.approx(2.0)


def test_ledger_record_uptake_can_override_only_selected_fields():
    ledger = DemandLedger(season_days=90, recommended_npk={"tomato": (90.0, 45.0, 45.0)})
    ledger.register(crop("tomato", area=0.5))
    ledger.record_uptake("TOMATO", water_mm=7.0, n_kg_ha=2.0)
    total = ledger.close_day()
    assert total.water_mm == pytest.approx(7.0)
    assert total.npk_kg_ha == pytest.approx((2.0, 0.25, 0.25))


def test_ledger_uses_growth_days_when_available_and_fallback_otherwise():
    ledger = DemandLedger(season_days=90, recommended_npk={"tomato": (60.0, 30.0, 30.0)})
    ledger.register(crop("tomato", growth_days=30))
    assert ledger.close_day().npk_kg_ha == pytest.approx((2.0, 1.0, 1.0))
    ledger.register(crop("tomato"))
    assert ledger.close_day().npk_kg_ha == pytest.approx((60.0 / 90, 30.0 / 90, 30.0 / 90))


def test_ledger_fallback_rates_warn_once_and_scale_by_nutrient_coefficient():
    ledger = DemandLedger(season_days=10)
    with pytest.warns(UserWarning, match="placeholder"):
        ledger.register(crop("unknown crop", nutrient=0.5, area=0.25))
    # Warning should be emitted only once per normalized crop name.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ledger.register(crop("UNKNOWN CROP", nutrient=0.5, area=0.25))
    assert not caught
    total = ledger.close_day()
    assert total.npk_kg_ha == pytest.approx(tuple(0.25 * rate * 0.5 / 10 for rate in DEFAULT_RECOMMENDED_NPK))


def test_ledger_rejects_bad_constructor_values_and_unknown_uptake_crop():
    with pytest.raises(ValueError, match="season days"):
        DemandLedger(season_days=0)
    with pytest.raises(ValueError, match="reference demand"):
        DemandLedger(reference_demand_mm_day=-1.0)
    ledger = DemandLedger()
    with pytest.raises(KeyError, match="has not requested resources"):
        ledger.record_uptake("tomato", water_mm=1.0)


def test_ledger_close_clears_the_day_and_reset_clears_registrations():
    ledger = DemandLedger(recommended_npk={"tomato": (90.0, 45.0, 45.0)})
    ledger.register(crop("tomato"))
    assert ledger.close_day().water_mm == pytest.approx(4.0)
    assert ledger.close_day().water_mm == pytest.approx(0.0)
    ledger.register(crop("tomato"))
    ledger.reset()
    assert ledger.close_day().water_mm == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TextureSoilFertilizerModel facade/integration
# ---------------------------------------------------------------------------


def test_facade_combines_model_availability_with_configured_factors():
    model = TextureSoilFertilizerModel(
        soil="loam",
        nutrients=NutrientApplication(100.0, 60.0, 60.0),
        irrigation=IrrigationSchedule(amount_mm=0.0),
        recommended_npk={"tomato": (100.0, 60.0, 60.0)},
    )
    greenhouse = SimpleNamespace(water_factor=0.4, nutrient_factor=0.3)
    result = model.resources_for_day(crop(), greenhouse, day_index=0)
    assert result.water_factor == pytest.approx(0.4)
    assert result.nutrient_factor == pytest.approx(0.3)


def test_facade_can_disable_config_factor_multiplication():
    model = TextureSoilFertilizerModel(
        nutrients=NutrientApplication(100.0, 60.0, 60.0),
        combine_with_config_factors=False,
        recommended_npk={"tomato": (100.0, 60.0, 60.0)},
    )
    greenhouse = SimpleNamespace(water_factor=0.0, nutrient_factor=0.0)
    result = model.resources_for_day(crop(), greenhouse, day_index=0)
    assert result.water_factor == pytest.approx(1.0)
    assert result.nutrient_factor == pytest.approx(1.0)


def test_facade_rejects_time_going_backwards_until_reinitialized():
    model = TextureSoilFertilizerModel(
        nutrients=NutrientApplication(100.0, 60.0, 60.0),
        recommended_npk={"tomato": (100.0, 60.0, 60.0)},
    )
    model.resources_for_day(crop(), GREENHOUSE, day_index=1)
    with pytest.raises(ValueError, match="non-decreasing order"):
        model.resources_for_day(crop(), GREENHOUSE, day_index=0)


def test_facade_initialization_resets_day_water_and_nutrient_state():
    model = TextureSoilFertilizerModel(
        nutrients=NutrientApplication(100.0, 60.0, 60.0),
        irrigation=IrrigationSchedule(amount_mm=20.0),
        recommended_npk={"tomato": (100.0, 60.0, 60.0)},
    )
    model.resources_for_day(crop(), GREENHOUSE, day_index=0)
    model.resources_for_day(crop(), GREENHOUSE, day_index=1)
    model.initialize(GREENHOUSE)
    snapshot = model.snapshot()
    assert snapshot["day"] == -1
    assert snapshot["available_water_mm"] == pytest.approx(snapshot["total_available_water_mm"])
    assert snapshot["gravitational_water_mm"] == pytest.approx(0.0)
    assert snapshot["cum_irrigation_mm"] == pytest.approx(0.0)
    assert snapshot["cum_n_applied"] == pytest.approx(0.0)


def test_facade_snapshot_reports_cumulative_drainage_and_nitrogen_leaching():
    model = TextureSoilFertilizerModel(
        soil="sandy_loam",
        nutrients=NutrientApplication(100.0, 60.0, 60.0),
        irrigation=IrrigationSchedule(amount_mm=60.0),
        root_zone_depth_m=0.6,
        recommended_npk={"tomato": (100.0, 60.0, 60.0)},
    )
    for day in range(5):
        model.resources_for_day(crop(), GREENHOUSE, day_index=day)
    snapshot = model.snapshot()
    assert snapshot["cum_drained_mm"] > 0.0
    assert snapshot["cum_n_leached"] > 0.0
    assert snapshot["cum_n_leached"] == pytest.approx(model.nutrient_pools.cumulative()["n_leached"])
    assert snapshot["cum_drained_mm"] == pytest.approx(model.water_balance.cumulative()["drained_mm"])


def test_facade_rejects_invalid_soil_or_hydraulic_configuration():
    with pytest.raises(ValueError, match="Unknown soil"):
        TextureSoilFertilizerModel(soil="peat")
    with pytest.raises(ValueError, match="hydraulic_source"):
        TextureSoilFertilizerModel(hydraulic_source="unknown")
