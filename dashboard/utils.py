import math

from dashboard.config import ORGAN_COLUMNS
from dashboard.config import SCORE_BANDS

def first_existing_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def available_organ_columns(df):
    return {
        column: label
        for column, label in ORGAN_COLUMNS.items()
        if column in df.columns
    }


def safe_number(value, default=0.0):
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass
    return default


def latest_value(series):
    if series is None or series.empty:
        return 0.0
    return safe_number(series.iloc[-1])


def format_biomass(value):
    return f"{safe_number(value):,.2f}"



def score_band(score):
    for label, low, high, _ in SCORE_BANDS:
        if score < high:
            return label
    return SCORE_BANDS[-1][0]