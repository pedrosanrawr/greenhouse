# Greenhouse - Computational Science

A Computational Science project developed using **Python** and **Streamlit** to implement, simulate, and visualize computational models.

## Project Overview

This project explores computational methods through simulations, numerical computations, and interactive visualizations.

> **Project Status:** In Development

## Tech Stack

- **Python** — Core programming language
- **Streamlit** — Interactive web application
- **NumPy** — Numerical computations
- **Matplotlib** — Data visualization
- **Pandas** — Data manipulation

## Project Structure

```text
greenhouse/
├── app.py
├── simulation/
├── data/
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd greenhouse
```

### 2. Set up a Python environment (Optional)

Using a virtual environment is **optional but recommended** to keep project dependencies separate from other Python projects.

To create a virtual environment on Windows:

```powershell
py -m venv .venv
```

Activate it using Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If you already have a Python environment with the required dependencies installed, you can use it instead.

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

The application will open in your browser, usually at [http://localhost:8501](http://localhost:8501).

## Development Workflow

1. Pull the latest changes from `main`.
2. Create a branch for your assigned task.
3. Commit changes using consistent commit messages.
4. Push your branch to GitHub.
5. Open a pull request for review before merging into `main`.

## License

For academic use. License to be determined.

## Milestones

1. Make the engine internally consistent
2. Establish automated correctness checks
3. Improve the biological model
4. Make outputs explain the model
5. Validate tomato performance
6. Refine usability and extendability 

## TBD
1. Core biomass and carbon accounting
    [] Define biomass and assimilation units
    [] Establish carbon/accounting rules
    [] Correct maintenance respiration
    [] Define reserve behavior
    [] Define biomass and senscence
    [] Prevent impossible states

2. Make greenhouse controls affect the simulation
    [] Temperature response
    [] Light input
    [] Nutrient limitation
    [] Ariflow
    [] Plant area and density 
    [] Input Validation

3. Build automated test suites
    [] Zero-light test
    [] Temperature boundary tests
    [] Limitation tests
    [] Biomass conesrvation tests
    [] Numerical Stability tests
    [] Repeatability tests
    [] INterface Integration Tests

4. Improve plant development and source-sink dynamics
    [] Define development stages
    [] Link development to time and environmnet
    [] Improve organ sink demand
    [] Define allocation rules
    [] Improve fruit set and filling
    [] Improve leaf area dynamics
    [] Establis yield accounting

5. Improve the streamlit results and diagnostic
    [] Organ biomass over time
    [] Total versus harvestable biomass
    [] Growth rate
    [] Source-sink diagnostics
    [] Environmental diagnostics
    [] Simulation Summary

6. Validate and calibrate against real tomato data
    [] Create a parameter register
    [] Obrain reference data
    [] Mathc simulation conditions
    [] Compare model predicitons
    [] Calibrate selected parameters
    [] Validate independently
    [] Document the model's valid scope
    
7. IMprove simulation workflow and usability
    [] INitial conditions
    [] Run config
    [] Scenario comparison
    [] Reproducible exports
    [] Error handling
8. prep for multiple props 



## Features to be implemented

1. Simulation Engine - Basic Ver. Done
    * Simulate 

## Current Changes

1. Update goal from yield to biomass as the primary target but also keeping yield as a secondary target.
