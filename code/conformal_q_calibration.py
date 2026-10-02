#!/usr/bin/env python3
"""Held-out finite-sample calibration of the coupling-misspecification budget q.

For each trusted calibration event i, let V_i be the number of source-to-common-
event coupling constraints that exclude the trusted latent event time.  Under
exchangeability of V_1,...,V_n,V_{n+1}, the split-conformal order statistic
below returns a prespecified q whose marginal future coverage is at least
1-alpha: P(V_{n+1} <= q_hat) >= 1-alpha.

This script validates the discrete finite-sample rule under an exchangeable
contamination generator and includes a deliberately shifted test distribution
to show that the guarantee is not claimed under distribution shift.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np

SEED = 20260914
M = 8
ALPHA = 0.05
N_CAL = 199
N_REPS = 20_000
# Discrete number of invalid coupling constraints per event.  The particular
# generator is only a reproducibility stress test; the theorem is distribution-free.
EXCHANGEABLE_P = np.array([0.62, 0.25, 0.10, 0.03, 0, 0, 0, 0, 0], dtype=float)
SHIFTED_TEST_P = np.array([0.20, 0.25, 0.25, 0.20, 0.10, 0, 0, 0, 0], dtype=float)


from interval_identification import conformal_q_budget


def run_scenario(rng: np.random.Generator, cal_p: np.ndarray, test_p: np.ndarray) -> dict:
    support = np.arange(M + 1)
    covered = 0
    q_hist: Counter[int] = Counter()
    excess = []
    for _ in range(N_REPS):
        cal = rng.choice(support, size=N_CAL, p=cal_p)
        qhat = conformal_q_budget(cal, ALPHA, M)
        vnew = int(rng.choice(support, p=test_p))
        q_hist[qhat] += 1
        covered += int(vnew <= qhat)
        excess.append(max(0, vnew - qhat))
    return {
        "coverage": covered / N_REPS,
        "q_distribution": {str(k): v / N_REPS for k, v in sorted(q_hist.items())},
        "mean_excess_violations_when_undercovered": float(np.mean([x for x in excess if x > 0])) if any(x > 0 for x in excess) else 0.0,
        "undercoverage_events": int(sum(x > 0 for x in excess)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    exch = run_scenario(rng, EXCHANGEABLE_P, EXCHANGEABLE_P)
    shifted = run_scenario(rng, EXCHANGEABLE_P, SHIFTED_TEST_P)
    nominal = 1 - ALPHA
    out = {
        "seed": SEED,
        "m_sources": M,
        "alpha": ALPHA,
        "nominal_coverage": nominal,
        "n_calibration_events": N_CAL,
        "n_repetitions": N_REPS,
        "exchangeable_generator_probabilities": EXCHANGEABLE_P.tolist(),
        "shifted_test_probabilities": SHIFTED_TEST_P.tolist(),
        "exchangeable": exch,
        "deliberate_distribution_shift": shifted,
        "checks": {
            "exchangeable_empirical_coverage_at_least_nominal_minus_mc_tol": exch["coverage"] >= nominal - 0.005,
            "shift_stress_is_lower_than_exchangeable": shifted["coverage"] < exch["coverage"],
        },
        "interpretation": (
            "The exchangeable result is a Monte Carlo check of the finite-sample order-statistic rule. "
            "The shifted scenario is deliberately outside the theorem and is included to expose, not hide, the assumption boundary."
        ),
    }
    path = Path(args.output) if args.output else Path(__file__).resolve().parents[1]/"data"/"output"/"conformal_q_calibration.summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
