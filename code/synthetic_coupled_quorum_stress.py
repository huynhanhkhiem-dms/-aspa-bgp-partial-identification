#!/usr/bin/env python3
"""Deterministic shared-event coupling stress test for Propositions 6-7.

This is an implementation/theory stress test, not an Internet timing model.
Each event has one latent source event theta. Source j observes A_j=theta+delta_j,
where delta_j lies in a known source-specific envelope. A width-w local bracket
is then drawn to contain A_j. The BGP geometry is represented by the exact
threshold boundary from Proposition 2, generated near A_j so timing uncertainty
is decision-relevant.
"""
from __future__ import annotations
import csv, json, random
from pathlib import Path
from interval_identification import (
    addition_bounds, removal_bounds, quorum_classification,
    coupled_quorum_classification, shared_transition_tension,
)

SEED=20260914
WIDTHS=[0.02,0.05,0.10,0.20,0.35]
N=20_000
M=8
K=5
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'


def local_episode(direction: str, boundary: float):
    # At tau=0, additions satisfy D>0 iff A>S, so set S=boundary.
    # Removals satisfy D>0 iff A<E, so set E=boundary.
    return (boundary,boundary+1.0) if direction=='addition' else (boundary-1.0,boundary)


def run_width(w: float):
    rng=random.Random(SEED+int(round(w*10000)))
    sep_amb=coup_amb=mid_err=coup_err=0
    coupled_resolved=separable_resolved=0
    reversals=infeasible=0
    true_positive=0
    tensions=[]
    for _ in range(N):
        direction='addition' if rng.random()<0.5 else 'removal'
        theta=rng.uniform(0.15,0.75)
        brackets=[]; delays=[]; episodes=[]; latent=[]; midpoint=[]
        for j in range(M):
            alpha=0.0
            beta=w*(0.10+0.20*j/(M-1))  # heterogeneous envelope widths: 0.1w..0.3w
            delta=rng.uniform(alpha,beta)
            a=theta+delta
            q=rng.random()
            l=a-q*w
            u=l+w
            # Generate the decision boundary around the true A_j. This makes the
            # threshold question nontrivial without claiming an Internet model.
            boundary=a+rng.uniform(-0.35,0.35)
            s,e=local_episode(direction,boundary)
            truth=(a>boundary) if direction=='addition' else (a<boundary)
            ahat=(l+u)/2.0
            mtruth=(ahat>boundary) if direction=='addition' else (ahat<boundary)
            brackets.append((l,u)); delays.append((alpha,beta)); episodes.append((s,e))
            latent.append(truth); midpoint.append(mtruth)
        true_quorum=sum(latent)>=K
        midpoint_quorum=sum(midpoint)>=K
        true_positive += true_quorum
        local_bounds=[
            (addition_bounds(l,u,s,e) if direction=='addition' else removal_bounds(l,u,s,e))
            for (l,u),(s,e) in zip(brackets,episodes)
        ]
        sep=quorum_classification(local_bounds,K,0.0)
        if sep=='quorum_ambiguous': sep_amb+=1
        else: separable_resolved+=1
        try:
            coup=coupled_quorum_classification(direction,brackets,delays,episodes,K,0.0)
        except ValueError:
            infeasible+=1
            continue
        tensions.append(shared_transition_tension(brackets,delays))
        if coup.classification=='quorum_ambiguous':
            coup_amb+=1
        else:
            coupled_resolved+=1
            pred=coup.classification=='quorum_confirmed'
            coup_err += pred!=true_quorum
        if sep!='quorum_ambiguous' and coup.classification!=sep:
            reversals+=1
        mid_err += midpoint_quorum!=true_quorum
    gain=100*(sep_amb-coup_amb)/N
    return {
        'bracket_width':w,'n_events':N,'sources_per_event':M,'quorum_k':K,
        'separable_ambiguous_pct':100*sep_amb/N,
        'coupled_ambiguous_pct':100*coup_amb/N,
        'ambiguity_reduction_pp':gain,
        'midpoint_quorum_error_pct':100*mid_err/N,
        'coupled_resolved_errors':coup_err,
        'coupled_resolved_pct':100*coupled_resolved/N,
        'separable_resolved_pct':100*separable_resolved/N,
        'separable_resolved_label_reversals':reversals,
        'shared_model_infeasible_events':infeasible,
        'true_quorum_positive_pct':100*true_positive/N,
        'max_model_tension':max(tensions) if tensions else None,
    }


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[run_width(w) for w in WIDTHS]
    csv_path=OUT/'synthetic_coupled_quorum_stress.csv'
    with csv_path.open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    summary={
        'seed':SEED,'n_events_per_width':N,'sources_per_event':M,'quorum_k':K,
        'generator':{
            'shared_event':'theta~Uniform(0.15,0.75)',
            'delay_envelope':'source j: [0, w*(0.10+0.20*j/7)]; delta_j uniform in its envelope',
            'local_bracket':'width w; random placement conditional on containing A_j=theta+delta_j',
            'decision_boundary':'c_j=A_j+Uniform(-0.35,0.35); exact tau=0 boundary from Proposition 2',
            'note':'dimensionless implementation stress test; not calibrated to Internet timing',
        },
        'rows':rows,
        'all_coupled_resolved_decisions_correct':all(r['coupled_resolved_errors']==0 for r in rows),
        'no_separable_resolved_label_reversal':all(r['separable_resolved_label_reversals']==0 for r in rows),
        'all_generated_shared_models_feasible':all(r['shared_model_infeasible_events']==0 for r in rows),
    }
    (OUT/'synthetic_coupled_quorum_stress.summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__': main()
