"""Crop parameter registry.

Add a new crop by creating plants/<crop_name>.py and adding its CropDefinition
to the tuple below. The registry key is always the crop's own name.
"""
from data.plants.tomato.tomato import TOMATO
from data.plants.potato import POTATO
from data.plants.sweet_potato import SWEET_POTATO
from data.plants.eggplant import EGGPLANT
from data.plants.sweet_pepper import SWEET_PEPPER
from data.plants.chili_pepper import CHILI_PEPPER
from data.plants.cucumber import CUCUMBER
from data.plants.ampalaya import AMPALAYA
from data.plants.okra import OKRA
from data.plants.sitaw import SITAW
from data.plants.upo import UPO
from data.plants.patola import PATOLA
from data.plants.kalabasa import KALABASA
from data.plants.pakwan import PAKWAN
from data.plants.pechay import PECHAY
from data.plants.kangkong import KANGKONG
from data.plants.alugbati import ALUGBATI
from data.plants.lettuce import LETTUCE
from data.plants.mustard_greens import MUSTARD_GREENS
from data.plants.kulitis import KULITIS
from data.plants.radish import RADISH
from data.plants.carrot import CARROT
from data.plants.onion import ONION
from data.plants.garlic import GARLIC
from data.plants.taro import TARO
from data.plants.mungbean import MUNGBEAN
from data.plants.snap_bean import SNAP_BEAN
from data.plants.cabbage import CABBAGE
from data.plants.basil import BASIL
from data.plants.sweet_corn import SWEET_CORN

CROPS = {
    crop.name: crop
    for crop in (
        TOMATO,
        POTATO,
        SWEET_POTATO,
        EGGPLANT,
        SWEET_PEPPER,
        CHILI_PEPPER,
        CUCUMBER,
        AMPALAYA,
        OKRA,
        SITAW,
        UPO,
        PATOLA,
        KALABASA,
        PAKWAN,
        PECHAY,
        KANGKONG,
        ALUGBATI,
        LETTUCE,
        MUSTARD_GREENS,
        KULITIS,
        RADISH,
        CARROT,
        ONION,
        GARLIC,
        TARO,
        MUNGBEAN,
        SNAP_BEAN,
        CABBAGE,
        BASIL,
        SWEET_CORN,
    )
}
