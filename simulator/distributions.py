import json
import numpy as np
from scipy import stats
from pathlib import Path

# ── Distribution registry ──────────────────────────────────────────────────
DIST_MAP = {
    'gamma':       stats.gamma,
    'lognorm':     stats.lognorm,
    'weibull_min': stats.weibull_min,
    'expon':       stats.expon
}


def load_fitted_params(filepath: str | Path) -> dict:
    """
    Load fitted distribution parameters from JSON.

    Parameters
    ----------
    filepath : path to fitted_distributions.json

    Returns
    -------
    dict with port names as keys, full parameter dicts as values
    """
    with open(filepath) as f:
        return json.load(f)


def get_distribution(dist_name: str, params: list):
    """
    Reconstruct a frozen scipy distribution from name and params list.

    Parameters
    ----------
    dist_name : str   — one of 'gamma', 'lognorm', 'weibull_min', 'expon'
    params    : list  — parameter list as stored in JSON (from scipy .fit())

    Returns
    -------
    Frozen scipy distribution ready to call .rvs(), .ppf(), .pdf() on
    """
    if dist_name not in DIST_MAP:
        raise ValueError(
            f"Unknown distribution '{dist_name}'. "
            f"Available: {list(DIST_MAP.keys())}"
        )
    return DIST_MAP[dist_name](*params)


def get_congestion_multiplier(
    congestion_index: float,
    port: str,
    fitted: dict
) -> float:
    """
    Compute port-specific congestion multiplier.

    Strategy per port (from EDA Section 6.1):
      Rotterdam : dampened positive  — 1 + 0.3 × (ci - 1)
      Singapore : inverse            — 1 - 0.5 × (ci - 1)
      Shanghai  : no adjustment      — 1.0

    Parameters
    ----------
    congestion_index : float  — current congestion index (1.0 = 2019 baseline)
    port             : str    — 'Rotterdam', 'Singapore', or 'Shanghai'
    fitted           : dict   — loaded from fitted_distributions.json

    Returns
    -------
    float multiplier, clipped to [0.5, 2.0]
    """
    strategy = fitted[port]['congestion_strategy']

    if strategy['type'] == 'dampened':
        multiplier = 1 + strategy['coefficient'] * (congestion_index - 1)
    elif strategy['type'] == 'inverse':
        multiplier = 1 - strategy['coefficient'] * (congestion_index - 1)
    else:  # 'none'
        multiplier = 1.0

    return float(np.clip(multiplier, 0.5, 2.0))