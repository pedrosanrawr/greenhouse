"""Crop parameter registry.

Add a new crop by creating plants/<crop_name>.py and importing its Species
instance into this registry.
"""
from data.plants.tomato import TOMATO

CROPS = {
	"Tomato": TOMATO,
}
