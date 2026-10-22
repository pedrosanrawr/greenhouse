"""Crop parameter registry.

Add a new crop by creating plants/<crop_name>.py and adding its CropDefinition
to the tuple below. The registry key is always the crop's own name.
"""
from data.plants.tomato.tomato import TOMATO
from data.plants.potato import POTATO
from data.plants.sweet_potato import SWEET_POTATO

CROPS = {crop.name: crop for crop in (TOMATO, POTATO, SWEET_POTATO)}