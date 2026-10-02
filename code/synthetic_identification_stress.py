#!/usr/bin/env python3
"""Deterministic synthetic stress test for interval identification.

The experiment is deliberately dimensionless and is not calibrated to Internet
traffic. It tests logical behavior under known latent transition times.
For each transition-bracket width, it generates addition and removal cases,
compares the sharp-bound classifier with a midpoint-imputation classifier, and
reports ambiguity and midpoint error.  Seed and generator are fixed.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np

SEED = 20260914
WIDTHS = (0.01, 0.05, 0.10, 0.25, 0.50)
N_PER_DIRECTION = 200_000


def _one(rng: np.random.Generator, width: float, direction: str):
    n = N_PER_DIRECTION
    L = rng.uniform(0.0, 1.0 - width, n)
    U = L + width
    A = rng.uniform(L, U)
    S = rng.uniform(0.0, 0.95, n)
    episode = rng.uniform(0.02, 0.45, n)
    E = np.minimum(1.0, S + episode)
    M = (L + U) / 2.0

    if direction == "addition":
        truth = np.maximum(0.0, np.minimum(E, A) - S)
        lo = np.maximum(0.0, np.minimum(E, L) - S)
        hi = np.maximum(0.0, np.minimum(E, U) - S)
        mid = np.maximum(0.0, np.minimum(E, M) - S)
    elif direction == "removal":
        truth = np.maximum(0.0, E - np.maximum(S, A))
        lo = np.maximum(0.0, E - np.maximum(S, U))
        hi = np.maximum(0.0, E - np.maximum(S, L))
        mid = np.maximum(0.0, E - np.maximum(S, M))
    else:
        raise ValueError(direction)

    truth_gap = truth > 0
    midpoint_gap = mid > 0
    definite = lo > 0
    no_gap = hi == 0
    ambiguous = ~(definite | no_gap)
    resolved = ~ambiguous
    safe_pred = definite

    if not np.all(safe_pred[resolved] == truth_gap[resolved]):
        raise AssertionError("identified classifier made an incorrect resolved decision")
    if not np.all((hi - lo) <= np.minimum(width, E - S) + 1e-12):
        raise AssertionError("analytic width bound failed")

    return {
        "bracket_width": width,
        "direction": direction,
        "n": n,
        "resolved_pct": float(100.0 * resolved.mean()),
        "ambiguous_pct": float(100.0 * ambiguous.mean()),
        "midpoint_error_pct": float(100.0 * (midpoint_gap != truth_gap).mean()),
        "midpoint_error_given_ambiguous_pct": float(
            100.0 * ((midpoint_gap != truth_gap) & ambiguous).sum() / max(1, ambiguous.sum())
        ),
        "max_identified_width": float(np.max(hi - lo)),
        "resolved_errors": int(np.sum(safe_pred[resolved] != truth_gap[resolved])),
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    for width in WIDTHS:
        for direction in ("addition", "removal"):
            rows.append(_one(rng, width, direction))

    csv_path = out_dir / "synthetic_identification_stress.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    pooled = []
    for width in WIDTHS:
        rr = [r for r in rows if r["bracket_width"] == width]
        pooled.append({
            "bracket_width": width,
            "n_total": sum(r["n"] for r in rr),
            "resolved_pct_mean": sum(r["resolved_pct"] for r in rr) / 2.0,
            "ambiguous_pct_mean": sum(r["ambiguous_pct"] for r in rr) / 2.0,
            "midpoint_error_pct_mean": sum(r["midpoint_error_pct"] for r in rr) / 2.0,
            "midpoint_error_given_ambiguous_pct_mean": sum(r["midpoint_error_given_ambiguous_pct"] for r in rr) / 2.0,
            "resolved_errors_total": sum(r["resolved_errors"] for r in rr),
        })

    summary = {
        "seed": SEED,
        "n_per_direction_per_width": N_PER_DIRECTION,
        "generator": {
            "transition_bracket": "L~Uniform(0,1-w), U=L+w, A~Uniform(L,U)",
            "bgp_episode": "S~Uniform(0,0.95), duration~Uniform(0.02,0.45), E=min(1,S+duration)",
            "note": "dimensionless stress test; not calibrated to Internet prevalence or timing",
        },
        "pooled_by_width": pooled,
        "all_resolved_decisions_correct": all(r["resolved_errors"] == 0 for r in rows),
    }
    (out_dir / "synthetic_identification_stress.summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
