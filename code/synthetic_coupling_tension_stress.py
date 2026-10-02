#!/usr/bin/env python3
"""Stress test for the shared-event model-tension certificate.

A clean event has one latent theta shared by eight source-local transitions.
A contaminated event replaces one source by a second latent event shifted by
``shift*w``.  The reported detection rate is the fraction for which the
shared-transition feasible set is empty (Delta>0).

This is a theorem/implementation stress test, not an Internet contamination
model and not an estimate of RPKI lineage error prevalence.
"""
from __future__ import annotations
import csv, json, random
from pathlib import Path
from interval_identification import shared_transition_tension, uniform_feasibility_slack

SEED=20260914
W=0.10
N=20_000
M=8
SHIFTS=[0.0,0.25,0.50,1.0,2.0]
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'


def one_run(mult: float):
    rng=random.Random(SEED+int(mult*10000)+9103)
    detected=0
    tensions=[]
    slacks=[]
    for _ in range(N):
        theta=rng.uniform(0.20,0.70)
        contaminated=rng.randrange(M)
        brackets=[]; delays=[]
        for j in range(M):
            alpha=0.0
            beta=W*(0.10+0.20*j/(M-1))
            base_theta=theta + (mult*W if (mult>0 and j==contaminated) else 0.0)
            delta=rng.uniform(alpha,beta)
            a=base_theta+delta
            q=rng.random()
            l=a-q*W
            u=l+W
            brackets.append((l,u)); delays.append((alpha,beta))
        d=shared_transition_tension(brackets,delays)
        s=uniform_feasibility_slack(brackets,delays)
        assert abs(s-d/2.0)<1e-12
        detected += d>1e-12
        tensions.append(d); slacks.append(s)
    positives=[x for x in tensions if x>1e-12]
    return {
        'shift_in_bracket_widths':mult,
        'n_events':N,
        'sources_per_event':M,
        'bracket_width':W,
        'infeasible_detected_pct':100*detected/N,
        'mean_positive_tension':sum(positives)/len(positives) if positives else 0.0,
        'max_tension':max(tensions),
        'max_uniform_slack':max(slacks),
    }


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[one_run(x) for x in SHIFTS]
    csvp=OUT/'synthetic_coupling_tension_stress.csv'
    with csvp.open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    summary={
        'seed':SEED,'n_events_per_shift':N,'sources_per_event':M,'bracket_width':W,
        'generator':{
            'clean':'all eight sources share theta; source delays lie in stated envelopes',
            'contamination':'one uniformly chosen source uses theta + shift*w before its valid delay',
            'interpretation':'detection evaluates incompatibility of the stated shared-event model; not Internet prevalence',
        },
        'rows':rows,
        'clean_false_positive_pct':rows[0]['infeasible_detected_pct'],
    }
    (OUT/'synthetic_coupling_tension_stress.summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__': main()
