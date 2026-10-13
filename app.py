
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Computational Science",
    page_icon="🔬",
    layout="wide"
)

st.title("Computational Science Simulation")
st.write("Edrick Estorel's Greenhouse")

st.sidebar.header("Simulation Parameters")

iterations = st.sidebar.slider(
    "Number of iterations",
    min_value=10,
    max_value=100,
    value=50
)

x = np.arange(iterations)
y = np.sin(x * 0.1)

fig, ax = plt.subplots()
ax.plot(x, y)
ax.set_xlabel("Iteration")
ax.set_ylabel("Value")
ax.set_title("Sample Simulation Output")

st.pyplot(fig)

st.success("The Streamlit app is running!")