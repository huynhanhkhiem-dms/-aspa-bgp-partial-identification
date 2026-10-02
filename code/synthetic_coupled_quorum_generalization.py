#!/usr/bin/env python3
"""Generalization stress test for strict shared-event quorum identification.

This deterministic implementation stress test varies the number of sources and
quorum threshold instead of relying on the single 5-of-8 configuration used in
the headline experiment. It is intentionally dimensionless and is not an
Internet timing model.
"""
from __future__ import annotations
import json, random
from pathlib import Path
from interval_identification import (
    addition_bounds, removal_bounds, quorum_classification,
    coupled_quorum_classification,
)

SEED = 20260915
WIDTHS = [0.05, 0.20, 0.35]
CONFIGS = [(4,3),(6,4),(8,5),(12,7),(16,9),(16,12)]
N = 5_000
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data'/'output'


def local_episode(direction: str, boundary: float):
    return (boundary, boundary+1.0) if direction=='addition' else (boundary-1.0, boundary)


def run_cell(m: int, k: int, w: float):
    rng = random.Random(SEED + 100000*m + 1000*k + int(round(w*10000)))
    sep_amb = coup_amb = 0
    coup_err = reversals = infeasible = 0
    for _ in range(N):
        direction = 'addition' if rng.random() < 0.5 else 'removal'
        theta = rng.uniform(0.15,0.75)
        brackets=[]; delays=[]; episodes=[]; truth=[]
        for j in range(m):
            alpha=0.0
            # Same relative envelope family as the headline strict-coupling stress,
            # generalized to arbitrary M.
            beta=w*(0.10 + (0.20*j/(m-1) if m>1 else 0.0))
            delta=rng.uniform(alpha,beta)
            a=theta+delta
            frac=rng.random()
            l=a-frac*w; u=l+w
            boundary=a+rng.uniform(-0.35,0.35)
            s,e=local_episode(direction,boundary)
            brackets.append((l,u)); delays.append((alpha,beta)); episodes.append((s,e))
            truth.append((a>boundary) if direction=='addition' else (a<boundary))
        true_quorum=sum(truth)>=k
        local_bounds=[
            addition_bounds(l,u,s,e) if direction=='addition' else removal_bounds(l,u,s,e)
            for (l,u),(s,e) in zip(brackets,episodes)
        ]
        sep=quorum_classification(local_bounds,k,0.0)
        if sep=='quorum_ambiguous': sep_amb += 1
        try:
            coup=coupled_quorum_classification(direction,brackets,delays,episodes,k,0.0)
        except ValueError:
            infeasible += 1
            continue
        if coup.classification=='quorum_ambiguous':
            coup_amb += 1
        else:
            pred=coup.classification=='quorum_confirmed'
            coup_err += pred != true_quorum
        if sep!='quorum_ambiguous' and coup.classification!=sep:
            reversals += 1
    return {
        'sources_per_event':m,'quorum_k':k,'bracket_width':w,'n_events':N,
        'separable_ambiguous_pct':100*sep_amb/N,
        'coupled_ambiguous_pct':100*coup_amb/N,
        'ambiguity_reduction_pp':100*(sep_amb-coup_amb)/N,
        'coupled_resolved_errors':coup_err,
        'separable_resolved_label_reversals':reversals,
        'shared_model_infeasible_events':infeasible,
    }


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[run_cell(m,k,w) for (m,k) in CONFIGS for w in WIDTHS]
    summary={
        'seed':SEED,
        'n_events_per_cell':N,
        'widths':WIDTHS,
        'configurations':[{'sources_per_event':m,'quorum_k':k} for m,k in CONFIGS],
        'rows':rows,
        'total_events':sum(r['n_events'] for r in rows),
        'all_coupled_resolved_decisions_correct':all(r['coupled_resolved_errors']==0 for r in rows),
        'no_separable_resolved_label_reversal':all(r['separable_resolved_label_reversals']==0 for r in rows),
        'all_generated_shared_models_feasible':all(r['shared_model_infeasible_events']==0 for r in rows),
        'ambiguity_reduction_pp_min':min(r['ambiguity_reduction_pp'] for r in rows),
        'ambiguity_reduction_pp_max':max(r['ambiguity_reduction_pp'] for r in rows),
        'note':'dimensionless implementation stress test; not calibrated to Internet timing',
    }
    path=OUT/'synthetic_coupled_quorum_generalization.summary.json'
    path.write_text(json.dumps(summary,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__':
    main()
