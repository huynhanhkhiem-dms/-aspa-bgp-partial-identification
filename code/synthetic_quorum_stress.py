#!/usr/bin/env python3
"""Deterministic multi-vantage quorum stress test.

For each synthetic event, eight source-local observation pairs share one
transition direction but have independent interval-censored observation
brackets and BGP episodes.  The latent source-local transition time is known
only to the simulator.  We compare a 5-of-8 quorum based on midpoint-imputed
local labels with the sharp quorum classification implied by local duration
bounds.

The generator is dimensionless and is not calibrated to Internet timing.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np

SEED = 20260914
WIDTHS = (0.01, 0.05, 0.10, 0.25, 0.50)
N_EVENTS_PER_WIDTH = 100_000
M_SOURCES = 8
K_QUORUM = 5


def _one_width(rng: np.random.Generator, width: float) -> dict:
    n = N_EVENTS_PER_WIDTH
    m = M_SOURCES
    direction = rng.integers(0, 2, size=n)  # 0=addition, 1=removal
    direction2 = direction[:, None]

    L = rng.uniform(0.0, 1.0 - width, size=(n, m))
    U = L + width
    A = rng.uniform(L, U)
    S = rng.uniform(0.0, 0.95, size=(n, m))
    episode = rng.uniform(0.02, 0.45, size=(n, m))
    E = np.minimum(1.0, S + episode)
    M = (L + U) / 2.0

    truth_add = np.maximum(0.0, np.minimum(E, A) - S)
    truth_rem = np.maximum(0.0, E - np.maximum(S, A))
    truth = np.where(direction2 == 0, truth_add, truth_rem)

    midpoint_add = np.maximum(0.0, np.minimum(E, M) - S)
    midpoint_rem = np.maximum(0.0, E - np.maximum(S, M))
    midpoint = np.where(direction2 == 0, midpoint_add, midpoint_rem)

    lo_add = np.maximum(0.0, np.minimum(E, L) - S)
    hi_add = np.maximum(0.0, np.minimum(E, U) - S)
    lo_rem = np.maximum(0.0, E - np.maximum(S, U))
    hi_rem = np.maximum(0.0, E - np.maximum(S, L))
    lo = np.where(direction2 == 0, lo_add, lo_rem)
    hi = np.where(direction2 == 0, hi_add, hi_rem)

    true_count = (truth > 0.0).sum(axis=1)
    midpoint_count = (midpoint > 0.0).sum(axis=1)
    lower_count = (lo > 0.0).sum(axis=1)
    upper_count = (hi > 0.0).sum(axis=1)

    truth_quorum = true_count >= K_QUORUM
    midpoint_quorum = midpoint_count >= K_QUORUM
    definite_positive = lower_count >= K_QUORUM
    definite_negative = upper_count < K_QUORUM
    resolved = definite_positive | definite_negative
    sharp_prediction = definite_positive

    resolved_errors = int(np.sum(sharp_prediction[resolved] != truth_quorum[resolved]))
    if resolved_errors:
        raise AssertionError("sharp quorum classifier made a resolved error")

    return {
        "bracket_width": width,
        "n_events": n,
        "sources_per_event": M_SOURCES,
        "quorum_k": K_QUORUM,
        "resolved_pct": float(100.0 * resolved.mean()),
        "ambiguous_pct": float(100.0 * (~resolved).mean()),
        "midpoint_quorum_error_pct": float(100.0 * (midpoint_quorum != truth_quorum).mean()),
        "true_quorum_positive_pct": float(100.0 * truth_quorum.mean()),
        "resolved_errors": resolved_errors,
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = [_one_width(rng, width) for width in WIDTHS]

    csv_path = out_dir / "synthetic_quorum_stress.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "seed": SEED,
        "n_events_per_width": N_EVENTS_PER_WIDTH,
        "sources_per_event": M_SOURCES,
        "quorum_k": K_QUORUM,
        "generator": {
            "transition_direction": "one shared addition/removal direction per event",
            "source_local_transition": "L~Uniform(0,1-w), U=L+w, A~Uniform(L,U) independently per source pair",
            "bgp_episode": "S~Uniform(0,0.95), duration~Uniform(0.02,0.45), E=min(1,S+duration)",
            "note": "dimensionless implementation stress test; not calibrated to Internet prevalence or timing",
        },
        "rows": rows,
        "all_resolved_quorum_decisions_correct": all(r["resolved_errors"] == 0 for r in rows),
    }
    (out_dir / "synthetic_quorum_stress.summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
