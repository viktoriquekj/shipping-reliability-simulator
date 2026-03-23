"""
tests/test_simulator.py

Unit tests for the Monte Carlo simulator.
Run with: pytest tests/ -v
"""

import numpy as np
import pytest
from scipy import stats
from simulator.route import Route, Segment
from simulator.monte_carlo import MonteCarloSimulator
from analysis.kpis import compute_kpis, compare_scenarios


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def simple_route():
    """Minimal two-segment route for fast testing."""
    return Route('Test Route', [
        Segment(
            name               = 'Transit leg',
            scheduled_days     = 10.0,
            delay_distribution = stats.norm(loc=10, scale=0.6),
            is_port            = False,
            congestion_port    = None
        ),
        Segment(
            name               = 'Port delay',
            scheduled_days     = 1.0,
            delay_distribution = stats.gamma(a=3.9, loc=0, scale=0.24),
            is_port            = True,
            congestion_port    = None   # no multiplier in unit test
        )
    ])


@pytest.fixture
def full_route():
    """Full Rotterdam → Singapore → Shanghai route for integration testing."""
    from simulator.distributions import get_distribution
    import json
    from pathlib import Path

    fitted_path = Path('data/processed/fitted_distributions.json')
    if not fitted_path.exists():
        pytest.skip("fitted_distributions.json not found — run Notebook 02 first")

    with open(fitted_path) as f:
        fitted = json.load(f)

    segments = [
        Segment('Rotterdam port delay', 1.0,
                get_distribution(fitted['Rotterdam']['best_distribution'],
                                 fitted['Rotterdam']['params']),
                is_port=True, congestion_port='Rotterdam'),
        Segment('Rotterdam → Singapore transit', 21.0,
                stats.norm(loc=21.0, scale=1.26),
                is_port=False),
        Segment('Singapore port delay', 1.0,
                get_distribution(fitted['Singapore']['best_distribution'],
                                 fitted['Singapore']['params']),
                is_port=True, congestion_port='Singapore'),
        Segment('Singapore → Shanghai transit', 4.0,
                stats.norm(loc=4.0, scale=0.24),
                is_port=False),
        Segment('Shanghai port delay', 1.0,
                get_distribution(fitted['Shanghai']['best_distribution'],
                                 fitted['Shanghai']['params']),
                is_port=True, congestion_port='Shanghai'),
    ]
    return Route('Rotterdam → Singapore → Shanghai', segments), fitted


# ── Reproducibility ────────────────────────────────────────────────────────

def test_reproducibility_same_seed(simple_route):
    """Same seed must always produce identical results."""
    sim1 = MonteCarloSimulator(simple_route, seed=42)
    sim2 = MonteCarloSimulator(simple_route, seed=42)
    np.testing.assert_array_equal(sim1.run(1000), sim2.run(1000))


def test_different_seeds_differ(simple_route):
    """Different seeds must produce different results."""
    sim1 = MonteCarloSimulator(simple_route, seed=42)
    sim2 = MonteCarloSimulator(simple_route, seed=99)
    assert not np.array_equal(sim1.run(1000), sim2.run(1000))


# ── Output validity ────────────────────────────────────────────────────────

def test_no_negative_values(simple_route):
    """All simulated journey times must be non-negative."""
    sim     = MonteCarloSimulator(simple_route, seed=42)
    results = sim.run(1000)
    assert (results >= 0).all(), "Found negative journey times"


def test_output_length(simple_route):
    """Output array length must equal n_iterations."""
    sim = MonteCarloSimulator(simple_route, seed=42)
    for n in [100, 1000, 5000]:
        results = sim.run(n)
        assert len(results) == n


def test_p90_greater_than_mean(simple_route):
    """P90 must always exceed the mean for right-skewed distributions."""
    sim     = MonteCarloSimulator(simple_route, seed=42)
    results = sim.run(5000)
    assert np.percentile(results, 90) > results.mean()


def test_p95_greater_than_p90(simple_route):
    """P95 must always exceed P90."""
    sim     = MonteCarloSimulator(simple_route, seed=42)
    results = sim.run(5000)
    assert np.percentile(results, 95) > np.percentile(results, 90)


# ── Summary KPIs ──────────────────────────────────────────────────────────

def test_summary_keys(simple_route):
    """Summary must contain all required KPI keys."""
    sim     = MonteCarloSimulator(simple_route, seed=42)
    sim.run(1000)
    summary = sim.summary()
    required_keys = [
        'scheduled_days', 'mean_days', 'std_days',
        'p50_days', 'p90_days', 'p95_days',
        'on_time_rate_pct', 'reliability_buffer_d',
        'n_iterations', 'seed'
    ]
    for key in required_keys:
        assert key in summary.index, f"Missing key: {key}"


def test_on_time_rate_bounds(simple_route):
    """On-time rate must be between 0 and 100."""
    sim     = MonteCarloSimulator(simple_route, seed=42)
    results = sim.run(5000)
    kpis    = compute_kpis(results, scheduled_days=11.0)
    assert 0 <= kpis['on_time_rate_pct'] <= 100


def test_summary_seed_recorded(simple_route):
    """Summary must record the seed used."""
    sim     = MonteCarloSimulator(simple_route, seed=77)
    sim.run(500)
    assert sim.summary()['seed'] == 77


# ── Segment contribution ──────────────────────────────────────────────────

def test_segment_contribution_sums_to_100(simple_route):
    """Segment percentage contributions must sum to ~100%."""
    sim = MonteCarloSimulator(simple_route, seed=42)
    sim.run(2000)
    contrib = sim.segment_contribution()
    total_pct = contrib['pct_of_total'].sum()
    assert abs(total_pct - 100.0) < 1.0, \
        f"Segment contributions sum to {total_pct:.2f}%, expected ~100%"


# ── KPI module ────────────────────────────────────────────────────────────

def test_compare_scenarios():
    """compare_scenarios must return one row per scenario."""
    rng = np.random.default_rng(42)
    scenarios = {
        'Baseline':   rng.gamma(4, 0.24, 1000),
        'High congestion': rng.gamma(4, 0.30, 1000)
    }
    df = compare_scenarios(scenarios, scheduled_days=27.0)
    assert len(df) == 2
    assert 'p90_days' in df.columns
    assert df.loc['High congestion', 'p90_days'] > \
           df.loc['Baseline', 'p90_days']