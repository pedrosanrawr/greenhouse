import streamlit as st

_CSS = """
<style> 
    :root {
        --greenlab-olive: #8C9857;
        --greenlab-olive-dark: #737F43;
        --greenlab-olive-light: #A5B273;
        --greenlab-background: #191919;
        --greenlab-card: #292929;
        --greenlab-border: #444444;
    }

    .stApp {
        background-color: var(--greenlab-background);
    }

    [data-testid="stHeader"] {
		background: transparent;
        height: 2.75rem;
    }

    [data-testid="stSidebar"] {
        background-color: #242424;
        border-right: 1px solid #3D3D3D;
    }
	
	[data-testid="stSidebarHeader"] {
        height: auto;
        padding-top: 0.75rem;
        padding-bottom: 0;
    }
	
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.5rem;
    }
	
	/* Main area + sidebar: gap between consecutive elements (default 1rem) */
    [data-testid="stVerticalBlock"] {
        gap: 0.6rem;
    }

    /* Sidebar can be tighter still */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.4rem;
    }
	

    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }

    [data-testid="stMetric"] {
        background-color: var(--greenlab-card);
        border: 1px solid var(--greenlab-border);
        padding: 16px;
        border-radius: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #BDBDBD;
    }

    [data-testid="stMetricValue"] {
        color: #F4F4F4;
    }

    [data-testid="stExpander"] {
        border: 1px solid #484848;
        border-radius: 12px;
    }
	
	/* Less empty room above "GREENLAB" */
    [data-testid="stSidebarUserContent"] {
        padding-top: 0.25rem;
        padding-bottom: 1rem;
    }

    /* Expanders: smaller header and body padding */
    [data-testid="stExpander"] summary {
        padding: 0.4rem 0.75rem;
    }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        padding: 0.25rem 0.75rem 0.5rem;
    }

    /* Widget labels sit closer to their inputs */
    [data-testid="stWidgetLabel"] {
        margin-bottom: 0.1rem;
    }

    /* Sliders have tall built-in padding */
    [data-testid="stSlider"] {
        padding-bottom: 0;
    }
	
    /* Bordered containers (like the Key insights box) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 0.5rem 0.75rem;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        padding: 10px 14px;
    }

    /* Overall page padding */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 1.5rem !important;
    }
	/* Headings carry their own large margins */
    h1, h2, h3, h4, h5 {
        padding-top: 0.2rem !important;
        padding-bottom: 0.3rem !important;
        margin-bottom: 0 !important;
    }

    /* st.divider() adds a lot of vertical space around the line */
    hr {
        margin: 0.6rem 0 !important;
    }

    /* Sidebar dividers can be even tighter */
    [data-testid="stSidebar"] hr {
        margin: 0.4rem 0 1.5rem 0 !important;
    }

    /* Captions: less space under chart titles */
    [data-testid="stCaptionContainer"] {
        margin-top: 0.15rem;
        margin-bottom: 0.25rem;
    }
	
    /* Space between sidebar section titles and the first widget */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        padding-bottom: 0.5rem !important;
    }

    .greenlab-subtitle {
        color: #BDBDBD;
        font-size: 0.92rem;
        margin-top: -0.5rem;
        margin-bottom: 1.2rem;
    }

    .greenlab-note {
        background-color: #242424;
        border-left: 4px solid var(--greenlab-olive);
        border-radius: 5px;
        padding: 12px 15px;
        color: #DDDDDD;
        font-size: 0.9rem;
    }

    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background-color: var(--greenlab-olive) !important;
        border-color: var(--greenlab-olive) !important;
        color: white !important;
    }

    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: var(--greenlab-olive) !important;
        border-color: var(--greenlab-olive) !important;
    }

    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {
        border-color: #555555;
    }

    .stSelectbox [data-baseweb="select"]:focus-within,
    .stMultiSelect [data-baseweb="select"]:focus-within {
        border-color: var(--greenlab-olive) !important;
        box-shadow: 0 0 0 1px var(--greenlab-olive) !important;
    }

    a {
        color: var(--greenlab-olive-light) !important;
    }

    hr {
        border-color: #414141;
    }
</style>
"""

def inject_styles():
	st.markdown(_CSS, unsafe_allow_html=True)