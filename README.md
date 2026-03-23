# Shipping Reliability Simulator

A Monte Carlo simulation engine for container shipping route reliability analysis,
built to evaluate network design performance under real-world variability.
Models the Rotterdam → Singapore → Shanghai trade lane using real port activity
and performance data from IMF PortWatch and UNCTAD.

---

## What it does

- Simulates 10,000+ voyages along a container shipping route
- Models port delays using probability distributions fitted to real UNCTAD data
- Applies port-specific congestion multipliers derived from IMF PortWatch data
- Quantifies reliability via P50/P90/P95 delivery times and on-time rates
- Identifies which ports and transit legs drive the most schedule variability
  via sensitivity analysis and tornado charts

---

## Why these three ports

The route Rotterdam → Singapore → Shanghai represents one of the highest-volume
container trade lanes in the world (Europe–Asia, ~25–30% of global container trade)
and covers three structurally distinct node types:

| Port | Role | Why included |
|---|---|---|
| Rotterdam | European origin hub | Largest container port in Europe, Maersk's primary EU gateway |
| Singapore | Mid-route transhipment hub | World's busiest transhipment port, critical relay on Asia–Europe lane |
| Shanghai Yangshan | Asian destination mega-port | World's busiest container port by TEU volume |

---

## Data Sources

| Dataset | Source | Used for |
|---|---|---|
| Daily port activity (2019–2026) | IMF PortWatch | Congestion index per port |
| Time in port — container ships (2018–2023) | UNCTAD | Port delay distribution fitting |
| Number of port calls — container ships (2018–2023) | UNCTAD | Congestion cross-validation |

> The IMF PortWatch disruption dataset was assessed but not used — zero GDACS-classified
> natural disaster events were recorded for our three ports in the 2022–2023 window.
> Tail risk is captured implicitly through right-skewed fitted distributions.

---

## Project Structure

```
shipping-reliability-simulator/
├── data/
│   ├── raw/                              # Source data (gitignored)
│   └── processed/                        # Cleaned outputs (committed)
│       ├── congestion_monthly.csv        # Monthly congestion index per port
│       ├── fitted_distributions.json     # Fitted distribution parameters
│       ├── ports_filtered.csv            # Daily data for 3 ports
│       ├── time_in_port_clean.csv        # UNCTAD cleaned data
│       └── port_calls_clean.csv          # UNCTAD port calls
├── figures/
│   ├── eda_part/                         # EDA visualisations
│   └── distribution_fitting/            # Fitting diagnostic plots
├── simulator/
│   ├── distributions.py                  # Load params, reconstruct distributions
│   ├── route.py                          # Route and Segment dataclasses
│   └── monte_carlo.py                    # Core simulation engine
├── analysis/
│   ├── kpis.py                           # Reliability metrics
│   └── sensitivity.py                    # Sensitivity analysis + tornado chart
├── notebooks/
│   ├── 01_eda_analysis.ipynb             # EDA and preprocessing
│   ├── 02_distribution_fitting.ipynb     # Distribution fitting
│   └── 03_simulation_results.ipynb       # Simulation outputs
├── tests/
│   ├── test_distributions.py             # Distribution loading and multiplier tests
│   └── test_simulator.py                 # Simulator reproducibility and KPI tests
├── outputs/                              # Simulation output files
├── requirements.txt
└── README.md
```

---

## Modelling Approach

### Route segments

| Segment | Type | Scheduled (days) | Distribution |
|---|---|---|---|
| Rotterdam port delay | Port | 1.0 | Gamma — fitted from UNCTAD |
| Rotterdam → Singapore transit | Transit | 21.0 | Normal(21.0, 1.26) |
| Singapore port delay | Port | 1.0 | Gamma — fitted from UNCTAD |
| Singapore → Shanghai transit | Transit | 4.0 | Normal(4.0, 0.24) |
| Shanghai port delay | Port | 1.0 | Gamma — fitted from UNCTAD |

**Total scheduled journey: 28 days**

### Fitted distributions

All three ports were best described by a **Gamma distribution** (selected by
minimum KS statistic from four candidates: Gamma, Log-normal, Weibull, Exponential).

| Port | Distribution | KS stat | p-value | Fitted mean | P90 |
|---|---|---|---|---|---|
| Rotterdam | Gamma(3.92, 0, 0.243) | 0.0139 | 0.829 | 0.952d | 1.596d |
| Singapore | Gamma(4.11, 0, 0.242) | 0.0123 | 0.921 | 0.992d | 1.648d |
| Shanghai  | Gamma(3.70, 0, 0.201) | 0.0144 | 0.795 | 0.746d | 1.265d |

Distributions were fitted by synthesising samples from 6 annual UNCTAD medians
(2018–2023) using CV=0.5 — a standard assumption for port dwell time variability.

### Port-specific congestion multipliers

EDA revealed that the congestion–dwell time relationship is port-specific:

| Port | r (congestion vs dwell) | Strategy | Formula |
|---|---|---|---|
| Rotterdam | −0.53 | Dampened | `1 + 0.3 × (CI − 1)` |
| Singapore | −0.89 | Inverse | `1 − 0.5 × (CI − 1)` |
| Shanghai  | +0.05 | None | `1.0` (no adjustment) |

### Transit time variability

Modelled as `Normal(μ=scheduled, σ=0.06×scheduled)` — a standard industry proxy
based on Sea-Intelligence schedule reliability benchmarks. No direct transit
time data was available.

### Monte Carlo engine

Runs N iterations (default 10,000). Each iteration independently samples from
all stochastic components and records the total journey time. Fixed seed
guarantees reproducible outputs.

```python
sim     = MonteCarloSimulator(route, seed=42, fitted_params=fitted)
results = sim.run(n_iterations=10_000)
print(sim.summary())
```

---

## Key Outputs

| KPI | Description |
|---|---|
| P50 (days) | Median journey time across all simulated voyages |
| P90 (days) | Journey time exceeded in only 10% of simulations |
| P95 (days) | Conservative planning buffer — exceeded in 5% of simulations |
| On-time rate (%) | Share of voyages completing within scheduled time + 1 day buffer |
| Reliability buffer (days) | Extra days needed beyond schedule to guarantee P90 delivery |

---

## Assumptions

| # | Assumption | Rationale |
|---|---|---|
| A1 | Transit variability: Normal(μ, σ=0.06μ) | Standard industry proxy — no direct data |
| A2 | UNCTAD time in port includes berth service time, not pure waiting time | Documented data limitation |
| A3 | Congestion baseline = 2019 mean daily calls (pre-COVID) | Last full unaffected year |
| A4 | Singapore 2018–2021 medians imputed via China ratio (×0.896) | UNCTAD data missing for those years |
| A5 | CV=0.5 for sample synthesis from annual medians | Standard port dwell time literature |
| A6 | No separate disruption layer | Zero GDACS events recorded for our 3 ports |
| A7 | All simulations seeded at 42 by default | Full reproducibility |

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

# Run tests
pytest tests/ -v
```

---

## Running the notebooks

```bash
# Must be run in order — each notebook depends on outputs from the previous
jupyter notebook notebooks/01_eda_analysis.ipynb
jupyter notebook notebooks/02_distribution_fitting.ipynb
jupyter notebook notebooks/03_simulation_results.ipynb
```

---

## Status

| Phase | Status |
|---|---|
| Project structure | ✅ Complete |
| Data collection | ✅ Complete |
| EDA & preprocessing | ✅ Complete |
| Distribution fitting | ✅ Complete |
| Simulator modules | ✅ Complete |
| Analysis modules | ✅ Complete |
| Notebook 03 — Results | ⏳ Pending |
| Tests | ✅ Complete |

---

## Author

Victoria Cojocaru
[LinkedIn](https://linkedin.com/in/yourprofile) · [GitHub](https://github.com/yourusername)
