import numpy as np
import pandas as pd
from simulator.route import Route
from simulator.distributions import get_congestion_multiplier


class MonteCarloSimulator:
    """
    Reproducible Monte Carlo simulator for container route reliability.

    Each run with the same seed produces identical results.
    Applies port-specific congestion multipliers from EDA analysis.

    Parameters
    ----------
    route              : Route object with fitted delay distributions
    seed               : int — random seed for reproducibility
    fitted_params      : dict — loaded from fitted_distributions.json
                         (required for congestion multiplier lookup)
    congestion_indices : dict — optional, port → congestion index value
                         defaults to 1.0 (baseline) for all ports

    Example
    -------
    sim     = MonteCarloSimulator(route, seed=42, fitted_params=fitted)
    results = sim.run(n_iterations=10_000)
    print(sim.summary())
    """

    def __init__(
        self,
        route: Route,
        seed: int = 42,
        fitted_params: dict = None,
        congestion_indices: dict = None
    ):
        self.route   = route
        self.seed    = seed
        self.fitted  = fitted_params
        self.results_ = None

        # Default congestion indices — 1.0 = baseline (no adjustment)
        self.congestion_indices = congestion_indices or {
            'Rotterdam': 1.0,
            'Singapore': 1.0,
            'Shanghai':  1.0
        }

    def run(self, n_iterations: int = 10_000) -> np.ndarray:
        """
        Run the Monte Carlo simulation.

        For each iteration:
          1. Sample delay from each segment's distribution
          2. Apply congestion multiplier to port segments
          3. Sum all segment delays → total journey time
          4. Record result

        Returns
        -------
        np.ndarray of shape (n_iterations,) — total journey times in days
        """
        rng = np.random.default_rng(self.seed)

        segment_draws = {}

        for seg in self.route.segments:
            # Draw raw samples from fitted distribution
            raw = seg.delay_distribution.rvs(
                size=n_iterations,
                random_state=rng
            )
            raw = np.maximum(raw, 0)  # no negative delays

            # Apply congestion multiplier to port segments
            if (seg.is_port
                    and seg.congestion_port is not None
                    and self.fitted is not None):

                ci = self.congestion_indices.get(seg.congestion_port, 1.0)
                multiplier = get_congestion_multiplier(
                    ci, seg.congestion_port, self.fitted
                )
                raw = raw * multiplier

            segment_draws[seg.name] = raw

        self.segment_draws_   = pd.DataFrame(segment_draws)
        self.results_         = self.segment_draws_.sum(axis=1).values
        self.n_iterations_    = n_iterations
        return self.results_

    def summary(self) -> pd.Series:
        """
        Compute reliability KPIs from simulation results.

        Returns
        -------
        pd.Series with all key metrics including seed and n_iterations
        """
        assert self.results_ is not None, \
            "Run .run() first before calling .summary()"

        r     = self.results_
        sched = self.route.scheduled_total

        return pd.Series({
            'route':                self.route.name,
            'scheduled_days':       round(sched, 2),
            'mean_days':            round(r.mean(), 4),
            'std_days':             round(r.std(), 4),
            'p50_days':             round(float(np.percentile(r, 50)), 4),
            'p75_days':             round(float(np.percentile(r, 75)), 4),
            'p90_days':             round(float(np.percentile(r, 90)), 4),
            'p95_days':             round(float(np.percentile(r, 95)), 4),
            'p99_days':             round(float(np.percentile(r, 99)), 4),
            'on_time_rate_pct':     round(
                                        float((r <= sched + 1).mean() * 100), 2
                                    ),
            'reliability_buffer_d': round(
                                        float(np.percentile(r, 90)) - sched, 4
                                    ),
            'n_iterations':         self.n_iterations_,
            'seed':                 self.seed
        })

    def segment_contribution(self) -> pd.DataFrame:
        """
        Compute mean and P90 contribution of each segment to total delay.

        Useful for identifying which segments drive the most variability.

        Returns
        -------
        pd.DataFrame sorted by mean_days descending
        """
        assert self.segment_draws_ is not None, \
            "Run .run() first"

        rows = []
        for col in self.segment_draws_.columns:
            s = self.segment_draws_[col]
            rows.append({
                'segment':      col,
                'mean_days':    round(s.mean(), 4),
                'std_days':     round(s.std(), 4),
                'p90_days':     round(float(np.percentile(s, 90)), 4),
                'pct_of_total': round(
                    s.mean() / self.results_.mean() * 100, 2
                )
            })

        return (
            pd.DataFrame(rows)
            .sort_values('mean_days', ascending=False)
            .reset_index(drop=True)
        )