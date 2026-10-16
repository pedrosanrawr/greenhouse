"""Shared, constant-condition environment model for the initial baseline."""
from data.models.contracts import EnvironmentModel
from data.models.types import EnvironmentConditions, GreenhouseConfig


class ConstantEnvironmentModel(EnvironmentModel):
    """Uses the user's configured conditions unchanged throughout the run.

    This is a baseline adapter, not a dynamic greenhouse climate simulation.
    Airflow is passed through for reporting but does not currently affect growth.
    """

    def conditions_for_day(
        self, greenhouse: GreenhouseConfig, day_index: int
    ) -> EnvironmentConditions:
        return EnvironmentConditions(
            temperature_c=greenhouse.temperature_c,
            light_hours=greenhouse.light_hours,
            irradiance_ppfd=greenhouse.irradiance_ppfd,
            airflow_m_s=greenhouse.airflow_m_s,
        )