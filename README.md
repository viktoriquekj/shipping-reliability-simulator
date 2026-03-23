# Shipping Reliability Simulator

A Monte Carlo simulation engine for container shipping route reliability analysis,
built to evaluate network design performance under real-world variability.
Models the Rotterdam → Singapore → Shanghai trade lane using real port activity,
disruption, and performance data from IMF PortWatch and UNCTAD.

---

## What it does

- Simulates 10,000+ voyages along a container shipping route
- Models port delays and transit time variability using fitted probability distributions
- Quantifies reliability via P50/P90/P95 delivery times and on-time rates
- Identifies which ports drive the most schedule variability via sensitivity analysis
- Incorporates real disruption events (cyclones, floods, geopolitical) as stochastic shocks

---

## Data Sources

| Dataset | Source | Used for |
|---|---|---|
| Daily port activity | IMF PortWatch | Congestion index per port |
| Disruption events | IMF PortWatch | Disruption probability & severity |
| Time in port (container ships, 2018–2023) | UNCTAD | Port delay distribution fitting |
| Number of port calls (container ships, 2018–2023) | UNCTAD | Congestion normalisation |

---

## Project Structure
```
shipping-reliability-simulator/
├── data/
│   ├── raw/                  # Source data (gitignored)
│   └── processed/            # Cleaned outputs (committed)
├── simulator/
│   ├── route.py              # Route and segment definitions
│   ├── distributions.py      # Distribution fitting and loading
│   └── monte_carlo.py        # Core simulation engine
├── analysis/
│   ├── kpis.py               # Reliability metrics
│   └── sensitivity.py        # Sensitivity analysis and tornado chart
├── notebooks/
│   ├── 01_eda.ipynb          # Exploratory data analysis
│   ├── 02_distribution_fitting.ipynb  # Fitting delay distributions
│   └── 03_simulation_results.ipynb   # Simulation outputs and visualisations
├── tests/
│   ├── test_distributions.py
│   └── test_simulator.py
├── requirements.txt
└── README.md
```

---

## Modelling Approach

### Route
Rotterdam → Singapore → Shanghai

Each leg of the route has two stochastic components:
- **Transit time** — Normal distribution centred on scheduled duration,
  with standard deviation set to 6% of scheduled days (standard industry proxy
  based on Sea-Intelligence schedule reliability benchmarks)
- **Port delay** — Fitted from UNCTAD median time in port data,
  scaled by a congestion multiplier derived from IMF PortWatch daily vessel calls

### Disruptions
Modelled as a Bernoulli process — each day carries a small probability of a
disruption event, fitted from historical disruption frequency in the PortWatch
dataset. When triggered, an additional delay is drawn from a severity distribution
calibrated to the alert level (GREEN / ORANGE / RED).

### Monte Carlo Engine
Runs N iterations (default 10,000). Each iteration independently samples from
all stochastic components and records the total journey time. The output
distribution is then summarised into reliability KPIs.

---

## Key Outputs

| KPI | Description |
|---|---|
| P50 (days) | Median journey time across all simulated voyages |
| P90 (days) | Journey time exceeded in only 10% of simulations |
| P95 (days) | Conservative planning buffer — exceeded in 5% of simulations |
| On-time rate (%) | Share of voyages completing within scheduled time + 1 day |
| Reliability buffer (days) | Extra days needed beyond schedule to guarantee P90 delivery |

---

## Assumptions

1. Transit time variability modelled as Normal(μ=scheduled, σ=0.06×scheduled)
   — no direct transit time data available; 6% std is a standard industry proxy
2. UNCTAD time in port is used as the baseline delay input — this includes
   berth service time, not pure waiting time
3. Congestion multiplier derived from PortWatch portcalls relative to
   2019 baseline (last full pre-COVID normal year)
4. Disruption events treated as independent — no spatial correlation modelled
5. All simulations use a fixed random seed (default: 42) for full reproducibility
6. No separate disruption layer modelled — the PortWatch disruption
   dataset (GDACS-sourced natural disasters) recorded zero events
   affecting Rotterdam, Singapore, or Shanghai in the 2022–2023
   observation window. Operational delay variability including
   tail risk is captured implicitly through right-skewed
   fitted distributions calibrated on real UNCTAD port stay data.

---

## Reproducibility

Every simulation run is seeded. Running with the same seed will always
produce identical outputs. Seed is logged in all KPI report outputs.
```python
sim = MonteCarloSimulator(route, seed=42)
results = sim.run(n_iterations=10_000)
```

---

## Setup
```bash
# Clone the repo
git clone https://github.com/yourusername/shipping-reliability-simulator
cd shipping-reliability-simulator

# Activate your environment
conda activate shipping-sim

# Install dependencies
pip install -r requirements.txt
```

---

## Status

| Phase | Status |
|---|---|
| Project structure | ✅ Complete |
| Data collection | ✅ Complete |
| EDA & preprocessing | 🔄 In progress |
| Distribution fitting | ⏳ Pending |
| Simulation engine | ⏳ Pending |
| Sensitivity analysis | ⏳ Pending |
| Tests | ⏳ Pending |

---

## Author

Victoria Cojocaru
[LinkedIn](https://linkedin.com/in/yourprofile) · [GitHub](https://github.com/yourusername)