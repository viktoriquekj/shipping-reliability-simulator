import numpy as np
import pandas as pd


def compute_kpis(
    results: np.ndarray,
    scheduled_days: float,
    buffer_days: float = 1.0,
    label: str = None
) -> pd.Series:
    """
    Compute reliability KPIs from Monte Carlo simulation output.

    Parameters
    ----------
    results        : np.ndarray — total journey times from simulation
    scheduled_days : float      — planned total journey time
    buffer_days    : float      — acceptable delay buffer for on-time calc
    label          : str        — optional scenario label

    Returns
    -------
    pd.Series of KPI values
    """
    r = np.array(results)

    kpis = {
        'scheduled_days':       round(scheduled_days, 2),
        'mean_days':            round(r.mean(), 4),
        'std_days':             round(r.std(), 4),
        'p50_days':             round(float(np.percentile(r, 50)), 4),
        'p75_days':             round(float(np.percentile(r, 75)), 4),
        'p90_days':             round(float(np.percentile(r, 90)), 4),
        'p95_days':             round(float(np.percentile(r, 95)), 4),
        'p99_days':             round(float(np.percentile(r, 99)), 4),
        'on_time_rate_pct':     round(
                                    float((r <= scheduled_days + buffer_days).mean() * 100), 2
                                ),
        'reliability_buffer_d': round(
                                    float(np.percentile(r, 90)) - scheduled_days, 4
                                ),
        'worst_case_days':      round(float(np.percentile(r, 99)), 4),
        'cv':                   round(r.std() / r.mean(), 4)
    }

    if label:
        kpis['scenario'] = label

    return pd.Series(kpis)


def compare_scenarios(
    scenarios: dict,
    scheduled_days: float,
    buffer_days: float = 1.0
) -> pd.DataFrame:
    """
    Compare KPIs across multiple simulation scenarios.

    Parameters
    ----------
    scenarios      : dict — {scenario_name: np.ndarray of results}
    scheduled_days : float
    buffer_days    : float

    Returns
    -------
    pd.DataFrame with one row per scenario
    """
    rows = []
    for name, results in scenarios.items():
        kpis = compute_kpis(results, scheduled_days, buffer_days, label=name)
        rows.append(kpis)

    df = pd.DataFrame(rows)
    if 'scenario' in df.columns:
        df = df.set_index('scenario')

    return df