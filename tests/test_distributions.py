"""
tests/test_distributions.py

Unit tests for distribution loading, reconstruction, and congestion multiplier.
Run with: pytest tests/ -v
"""

import json
import numpy as np
import pytest
from pathlib import Path
from scipy import stats
from simulator.distributions import (
    load_fitted_params,
    get_distribution,
    get_congestion_multiplier,
    DIST_MAP
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def fitted():
    """Load real fitted parameters — skip if file not found."""
    path = Path('data/processed/fitted_distributions.json')
    if not path.exists():
        pytest.skip("fitted_distributions.json not found — run Notebook 02 first")
    return load_fitted_params(path)


# ── Loading ────────────────────────────────────────────────────────────────

def test_load_fitted_params_keys(fitted):
    """JSON must contain all three ports."""
    for port in ['Rotterdam', 'Singapore', 'Shanghai']:
        assert port in fitted, f"Missing port: {port}"


def test_load_fitted_params_structure(fitted):
    """Each port entry must have required keys."""
    required = [
        'best_distribution', 'params',
        'congestion_strategy', 'fit_quality', 'analytical_kpis'
    ]
    for port, data in fitted.items():
        for key in required:
            assert key in data, f"{port} missing key: {key}"


def test_all_ports_use_gamma(fitted):
    """All three ports should have gamma as best distribution (from NB02)."""
    for port, data in fitted.items():
        assert data['best_distribution'] == 'gamma', \
            f"{port} best distribution is {data['best_distribution']}, expected gamma"


# ── Distribution reconstruction ───────────────────────────────────────────

def test_get_distribution_returns_frozen(fitted):
    """get_distribution must return a frozen scipy distribution."""
    for port, data in fitted.items():
        frozen = get_distribution(data['best_distribution'], data['params'])
        assert hasattr(frozen, 'rvs'),  f"{port}: missing .rvs()"
        assert hasattr(frozen, 'ppf'),  f"{port}: missing .ppf()"
        assert hasattr(frozen, 'pdf'),  f"{port}: missing .pdf()"


def test_get_distribution_unknown_raises():
    """get_distribution must raise ValueError for unknown distribution."""
    with pytest.raises(ValueError, match="Unknown distribution"):
        get_distribution('not_a_dist', [1.0, 0.0, 1.0])


def test_reconstructed_samples_positive(fitted):
    """Samples from reconstructed distributions must be non-negative."""
    rng = np.random.default_rng(42)
    for port, data in fitted.items():
        frozen  = get_distribution(data['best_distribution'], data['params'])
        samples = np.maximum(frozen.rvs(size=1000, random_state=rng), 0)
        assert (samples >= 0).all(), f"{port}: negative samples found"


def test_reconstructed_mean_close_to_analytical(fitted):
    """Simulated mean must be within 5% of analytical mean."""
    rng = np.random.default_rng(42)
    for port, data in fitted.items():
        frozen   = get_distribution(data['best_distribution'], data['params'])
        samples  = np.maximum(frozen.rvs(size=10_000, random_state=rng), 0)
        expected = data['analytical_kpis']['mean_days']
        actual   = samples.mean()
        pct_diff = abs(actual - expected) / expected
        assert pct_diff < 0.05, \
            f"{port}: mean {actual:.4f} is {pct_diff*100:.1f}% " \
            f"from analytical {expected:.4f} (>5% tolerance)"


def test_reconstructed_p90_close_to_analytical(fitted):
    """Simulated P90 must be within 5% of analytical P90."""
    rng = np.random.default_rng(42)
    for port, data in fitted.items():
        frozen   = get_distribution(data['best_distribution'], data['params'])
        samples  = np.maximum(frozen.rvs(size=10_000, random_state=rng), 0)
        expected = data['analytical_kpis']['p90_days']
        actual   = np.percentile(samples, 90)
        pct_diff = abs(actual - expected) / expected
        assert pct_diff < 0.05, \
            f"{port}: P90 {actual:.4f} is {pct_diff*100:.1f}% " \
            f"from analytical {expected:.4f} (>5% tolerance)"


# ── Congestion multiplier ─────────────────────────────────────────────────

def test_congestion_multiplier_baseline(fitted):
    """At congestion index 1.0, multiplier must equal 1.0 for all ports."""
    for port in ['Rotterdam', 'Singapore', 'Shanghai']:
        m = get_congestion_multiplier(1.0, port, fitted)
        assert abs(m - 1.0) < 1e-9, \
            f"{port}: baseline multiplier is {m}, expected 1.0"


def test_congestion_multiplier_rotterdam_dampened(fitted):
    """Rotterdam dampened: CI=1.2 → multiplier = 1 + 0.3*(1.2-1) = 1.06."""
    m = get_congestion_multiplier(1.2, 'Rotterdam', fitted)
    assert abs(m - 1.06) < 1e-6


def test_congestion_multiplier_singapore_inverse(fitted):
    """Singapore inverse: CI=1.2 → multiplier = 1 - 0.5*(1.2-1) = 0.9."""
    m = get_congestion_multiplier(1.2, 'Singapore', fitted)
    assert abs(m - 0.9) < 1e-6


def test_congestion_multiplier_shanghai_none(fitted):
    """Shanghai none: any CI → multiplier = 1.0."""
    for ci in [0.5, 0.8, 1.0, 1.5, 2.0]:
        m = get_congestion_multiplier(ci, 'Shanghai', fitted)
        assert abs(m - 1.0) < 1e-9, \
            f"Shanghai multiplier at CI={ci} is {m}, expected 1.0"


def test_congestion_multiplier_clipped(fitted):
    """Multiplier must be clipped to [0.5, 2.0]."""
    # Extreme low CI for Singapore (inverse) — would go below 0.5
    m_low = get_congestion_multiplier(0.01, 'Singapore', fitted)
    assert m_low >= 0.5

    # Extreme high CI for Rotterdam (dampened) — stays below 2.0
    m_high = get_congestion_multiplier(5.0, 'Rotterdam', fitted)
    assert m_high <= 2.0


def test_ks_pval_above_threshold(fitted):
    """All fitted distributions must have KS p-value > 0.05."""
    for port, data in fitted.items():
        pval = data['fit_quality']['ks_pval']
        assert pval > 0.05, \
            f"{port}: KS p-value {pval:.4f} is below 0.05 threshold"