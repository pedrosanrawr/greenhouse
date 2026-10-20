# dashboard/placeholder.py
from dataclasses import dataclass

import numpy as np
import pandas as pd

from dashboard.utils import score_band

COMPONENTS = ["Temperature", "Light", "Water", "Nutrients", "Airflow"]
ORGANS = ["Leaf", "Stem", "Root", "Flower", "Fruit"]


@dataclass
class PlaceholderData:
    scores: pd.DataFrame       # crop, score, limiting, band (sorted best first)
    components: pd.DataFrame   # rows = crops, columns = COMPONENTS
    yields: pd.DataFrame       # crop, yield_g, biomass_g, harvest_index
    organs: pd.DataFrame       # crop, organ, biomass
    cumulative: pd.DataFrame   # crop, day, yield_g
    stress: pd.DataFrame       # rows = crops, columns = days (0-1, 1 = no stress)


def build_placeholder(crops, days):
    days = max(int(days), 2)
    t = np.arange(1, days + 1)
    comp_rows, score_rows, yield_rows = {}, [], []
    organ_rows, cum_rows, stress_rows = [], [], {}

    for crop in crops:
        # Seeded per crop so values stay stable between reruns
        rng = np.random.default_rng(sum(ord(c) for c in crop))

        comp = rng.uniform(45, 98, len(COMPONENTS)).round(0)
        comp_rows[crop] = comp
        score = float(comp.mean())
        score_rows.append({
            "crop": crop,
            "score": score,
            "limiting": COMPONENTS[int(comp.argmin())],
            "band": score_band(score),
        })

        organ_values = rng.uniform(5, 60, len(ORGANS))
        biomass = float(organ_values.sum())
        yield_g = float(organ_values[3:].sum() * rng.uniform(0.5, 0.9))
        yield_rows.append({
            "crop": crop,
            "yield_g": yield_g,
            "biomass_g": biomass,
            "harvest_index": yield_g / biomass * 100,
        })
        for organ, value in zip(ORGANS, organ_values):
            organ_rows.append({"crop": crop, "organ": organ, "biomass": float(value)})

        steepness = rng.uniform(0.06, 0.1)
        midpoint = days * rng.uniform(0.5, 0.7)
        cumulative = yield_g / (1 + np.exp(-steepness * (t - midpoint)))
        for day, value in zip(t, cumulative):
            cum_rows.append({"crop": crop, "day": int(day), "yield_g": float(value)})

        wave = 0.15 * np.sin(t / rng.uniform(8, 15))
        noise = rng.normal(0, 0.04, days)
        stress_rows[crop] = np.clip(score / 100 + wave + noise, 0, 1)

    scores = (
        pd.DataFrame(score_rows)
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )
    return PlaceholderData(
        scores=scores,
        components=pd.DataFrame(comp_rows, index=COMPONENTS).T,
        yields=pd.DataFrame(yield_rows),
        organs=pd.DataFrame(organ_rows),
        cumulative=pd.DataFrame(cum_rows),
        stress=pd.DataFrame(stress_rows, index=t).T,
    )