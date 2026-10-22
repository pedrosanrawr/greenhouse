"""Tomato yield model: the fruit model with tomato as its (provisional) defaults.

All numbers live in FruitYieldParameters and are TEST VALUES. See fruit_yield.py.
"""
from data.models.fruit_yield import FruitYieldModel, FruitYieldParameters

TomatoYieldParameters = FruitYieldParameters


class TomatoYieldModel(FruitYieldModel):
    """Indeterminate greenhouse tomato, picked repeatedly."""