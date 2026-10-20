# dashboard/sections/header.py
import streamlit as st

from dashboard.config import COVER_TYPE


def render_header(settings, n_crops, warnings):
    left, right = st.columns([3, 1.4], vertical_alignment="center")

    with left:
        st.markdown("## Greenlab Simulator")
        st.caption(
            f"{settings.preset_name} · {settings.simulation_days} days · "
            f"starting {settings.start_date.isoformat()} · "
            f"{n_crops} crop(s) · {COVER_TYPE}"
        )

    with right:
        if warnings:
            with st.expander(f"⚠ {len(warnings)} input note(s)"):
                for message in warnings:
                    st.caption(message)