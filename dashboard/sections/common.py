# dashboard/sections/common.py
import streamlit as st

CHART_CONFIG = {"displayModeBar": False}


def section_header(title, subtitle=None, placeholder=False):
    suffix = "  🧪" if placeholder else ""
    st.markdown(f"### {title}{suffix}")
    if subtitle:
        st.caption(subtitle)


def how_to_read(text):
    """Plain-text explanation shown directly under a title. Call it BEFORE the chart."""
    st.caption(f"ⓘ {text}")