import pytest

from data.models.light import calculate_light


def calculate(**overrides):
    params = {
        "solar_radiation_mj_m2_day": 15.0,
        "leaf_biomass_g": 10.0,
        "sla_m2_g": 0.02,
        "extinction_k": 0.7,
        "area_per_plant_m2": 0.25,
        "cover_par_transmittance": 0.86,
    }
    params.update(overrides)
    return calculate_light(**params)


def test_zero_solar_means_zero_intercepted_par():
    result = calculate(solar_radiation_mj_m2_day=0.0)
    assert result.ipar_mj_m2_day == 0.0


def test_zero_leaf_biomass_means_zero_interception():
    result = calculate(leaf_biomass_g=0.0)
    assert result.lai == 0.0
    assert result.intercepted_fraction == 0.0
    assert result.ipar_mj_m2_day == 0.0


def test_interception_is_between_zero_and_one():
    result = calculate()
    assert 0.0 <= result.intercepted_fraction <= 1.0


def test_more_leaf_area_increases_interception():
    low = calculate(leaf_biomass_g=5.0)
    high = calculate(leaf_biomass_g=20.0)

    assert high.lai > low.lai
    assert high.intercepted_fraction > low.intercepted_fraction


def test_more_transmittance_increases_ipar():
    low = calculate(cover_par_transmittance=0.50)
    high = calculate(cover_par_transmittance=0.90)

    assert high.ipar_mj_m2_day > low.ipar_mj_m2_day


def test_invalid_transmittance_is_rejected():
    with pytest.raises(ValueError):
        calculate(cover_par_transmittance=1.5)