import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from simulator.monte_carlo import MonteCarloSimulator
from simulator.route import Route, Segment


def run_sensitivity(
    simulator: MonteCarloSimulator,
    shock_pct: float = 0.30,
    n_iterations: int = 10_000,
    metric: str = 'p90'
) -> pd.DataFrame:
    """
    Sensitivity analysis — stress-test each segment independently.

    For each segment, increase its distribution's scale parameter by
    shock_pct and measure the change in the chosen metric vs baseline.

    Parameters
    ----------
    simulator    : MonteCarloSimulator — already configured with route
    shock_pct    : float — fractional shock to apply (0.30 = +30%)
    n_iterations : int   — iterations per shocked simulation
    metric       : str   — 'p90', 'p95', 'mean', or 'on_time_rate_pct'

    Returns
    -------
    pd.DataFrame sorted by absolute impact descending (tornado order)
    """
    # Run baseline
    base_results = simulator.run(n_iterations)
    base_metric  = _extract_metric(
        base_results, metric, simulator.route.scheduled_total
    )

    records = []

    for i, seg in enumerate(simulator.route.segments):
        # Build shocked route — only segment i is shocked
        shocked_segments = []
        for j, s in enumerate(simulator.route.segments):
            if i == j:
                shocked_dist = _shock_distribution(
                    s.delay_distribution, shock_pct
                )
                shocked_segments.append(
                    Segment(
                        name               = s.name,
                        scheduled_days     = s.scheduled_days,
                        delay_distribution = shocked_dist,
                        is_port            = s.is_port,
                        congestion_port    = s.congestion_port
                    )
                )
            else:
                shocked_segments.append(s)

        shocked_route = Route(simulator.route.name, shocked_segments)
        shocked_sim   = MonteCarloSimulator(
            route              = shocked_route,
            seed               = simulator.seed,
            fitted_params      = simulator.fitted,
            congestion_indices = simulator.congestion_indices
        )
        shocked_results = shocked_sim.run(n_iterations)
        shocked_metric  = _extract_metric(
            shocked_results, metric, simulator.route.scheduled_total
        )

        delta = shocked_metric - base_metric

        records.append({
            'segment':        seg.name,
            'is_port':        seg.is_port,
            'base_metric':    round(base_metric, 4),
            'shocked_metric': round(shocked_metric, 4),
            'delta':          round(delta, 4),
            'delta_pct':      round(delta / base_metric * 100, 2)
        })

    df = (
        pd.DataFrame(records)
        .assign(abs_delta=lambda x: x['delta'].abs())
        .sort_values('abs_delta', ascending=False)
        .drop(columns='abs_delta')
        .reset_index(drop=True)
    )
    return df


def _extract_metric(
    results: np.ndarray,
    metric: str,
    scheduled_days: float
) -> float:
    """Extract a single scalar metric from simulation results."""
    if metric == 'p90':
        return float(np.percentile(results, 90))
    elif metric == 'p95':
        return float(np.percentile(results, 95))
    elif metric == 'mean':
        return float(results.mean())
    elif metric == 'on_time_rate_pct':
        return float((results <= scheduled_days + 1).mean() * 100)
    else:
        raise ValueError(
            f"Unknown metric '{metric}'. "
            f"Choose from: p90, p95, mean, on_time_rate_pct"
        )


def _shock_distribution(frozen_dist, shock_pct: float):
    args = list(frozen_dist.args)
    kwds = dict(frozen_dist.kwds)

    if args:
        # scale is the last positional arg
        args[-1] = args[-1] * (1 + shock_pct)
    elif 'scale' in kwds:
        # scale was passed as a keyword argument
        kwds['scale'] = kwds['scale'] * (1 + shock_pct)
    else:
        raise ValueError(
            f"Cannot locate scale parameter in distribution "
            f"'{frozen_dist.dist.name}': args={args}, kwds={kwds}"
        )

    return frozen_dist.dist(*args, **kwds)


def plot_tornado(
    sensitivity_df: pd.DataFrame,
    base_metric_value: float,
    shock_pct: float = 0.30,
    metric_label: str = 'P90 journey time (days)',
    color_positive: str = '#F44336',
    color_negative: str = '#4CAF50'
) -> plt.Figure:
    """
    Plot a tornado chart of sensitivity analysis results.

    Parameters
    ----------
    sensitivity_df     : output of run_sensitivity()
    base_metric_value  : float — baseline metric value (for title)
    shock_pct          : float — shock applied (for title)
    metric_label       : str   — axis label
    color_positive     : str   — bar color for positive delta (delay increase)
    color_negative     : str   — bar color for negative delta (delay decrease)

    Returns
    -------
    matplotlib Figure
    """
    df = sensitivity_df.sort_values('delta', ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(5, len(df) * 0.7)))

    colors = [
        color_positive if v >= 0 else color_negative
        for v in df['delta']
    ]

    bars = ax.barh(
        df['segment'],
        df['delta'],
        color=colors,
        alpha=0.85,
        height=0.55,
        edgecolor='white'
    )

    # Value labels on bars
    for bar, val in zip(bars, df['delta']):
        sign = '+' if val >= 0 else ''
        xpos = val + 0.005 if val >= 0 else val - 0.005
        ha   = 'left' if val >= 0 else 'right'
        ax.text(
            xpos, bar.get_y() + bar.get_height() / 2,
            f'{sign}{val:.3f}d',
            va='center', ha=ha,
            fontsize=9.5, fontweight='bold',
            color=color_positive if val >= 0 else color_negative
        )

    ax.axvline(0, color='black', linewidth=1.2)

    # Colour port vs transit labels differently
    port_segs = df[df['is_port']]['segment'].tolist()
    for label in ax.get_yticklabels():
        if label.get_text() in port_segs:
            label.set_color('#1565C0')
            label.set_fontweight('bold')

    ax.set_xlabel(f'Change in {metric_label}', fontsize=11)
    ax.set_title(
        f'Sensitivity Analysis — Impact of +{int(shock_pct * 100)}% '
        f'Shock on Each Segment\n'
        f'Base {metric_label}: {base_metric_value:.2f}d  |  '
        f'Blue = port segments',
        fontweight='bold', fontsize=11
    )

    pos_patch = plt.Rectangle((0, 0), 1, 1, fc=color_positive, alpha=0.85)
    neg_patch = plt.Rectangle((0, 0), 1, 1, fc=color_negative, alpha=0.85)
    ax.legend(
        [pos_patch, neg_patch],
        ['Delay increases (risk)', 'Delay decreases'],
        fontsize=9, loc='lower right'
    )

    plt.tight_layout()
    return fig