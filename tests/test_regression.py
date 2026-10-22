"""Regression tests for dashboard integration fixes in the greenhouse runner."""

from copy import deepcopy
from datetime import date
from types import SimpleNamespace

from dashboard.runner import configure_soil_model, run_all_crops
from data.models.compatibility import (
    SOIL_SUITABILITY,
    crop_compatibility,
)
from data.models.water_budget import water_requirement_mm_day
from data.plants import CROPS


def _settings(selected_crops, *, water_budget=12.0, texture="clay_loam"):
    return SimpleNamespace(
        selected_crops=selected_crops,
        temperature=25.0,
        airflow=0.4,
        relative_humidity_pct=70.0,
        water_budget_mm_day=water_budget,
        fertilizer_npk=(100.0, 60.0, 60.0),
        simulation_days=3,
        start_date=date(2025, 1, 1),
        soil_texture=texture,
    )


def test_runner_allocates_water_using_the_same_unverified_requirements_as_sidebar():
    selected = ["Tomato", "Potato", "Sweet potato"]
    outcome = run_all_crops(_settings(selected))

    assert not outcome.errors
    assert outcome.water_allocation is not None
    requirements = {
        name: water_requirement_mm_day(
            CROPS[name].parameters,
            allow_unverified=True,
        )
        for name in selected
    }
    expected_total = sum(requirements.values())

    assert outcome.water_allocation.total_requirement_mm_day == expected_total
    for name in selected:
        expected_supply = 12.0 * requirements[name] / expected_total
        assert abs(outcome.water_allocation.supply_mm_day[name] - expected_supply) < 1e-9


def test_configure_soil_model_applies_texture_before_run_inputs():
    crop = deepcopy(CROPS["Tomato"])
    problems = configure_soil_model(
        crop,
        water_mm_day=1.25,
        requirement_mm_day=3.8,
        npk_kg_ha=(100.0, 60.0, 60.0),
        soil_texture="sandy_loam",
    )

    assert not problems
    assert crop.soil_model.water_balance.profile.texture.name == "Sandy loam"
    assert crop.soil_model.water_balance.irrigation.amount_mm == 1.25
    assert crop.soil_model.nutrient_pools.application.n_kg_ha == 100.0


def test_compatibility_displays_numeric_unverified_water_requirement():
    params = CROPS["Carrot"].parameters
    result = crop_compatibility(
        params,
        temperature_c=20.0,
        run_days=120,
        name="Carrot",
    )

    expected = water_requirement_mm_day(params, allow_unverified=True)
    assert expected is not None
    assert result.water_requirement_mm_day == expected


def test_soil_suitability_preserves_unsuitable_and_onion_ratings():
    assert SOIL_SUITABILITY["carrot"]["ratings"]["clay"] == 0.0
    assert "onion" in SOIL_SUITABILITY
