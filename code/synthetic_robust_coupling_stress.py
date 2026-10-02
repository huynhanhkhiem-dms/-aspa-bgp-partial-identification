#!/usr/bin/env python3
"""Deterministic contamination stress test for robust coupled quorum bounds.

Every source-local transition bracket remains valid for the target transition.
Seven of eight source-to-common-event delay envelopes are valid. One source's
true delay is displaced by ``shift*w`` beyond the value drawn from its stated
envelope, so at most one coupling constraint is misspecified. This tests the
difference between strict q=0 coupling and robust q=1 downstream partial
identification. It is not an Internet contamination model or prevalence study.
"""
from __future__ import annotations
import csv, json, random
from pathlib import Path
from interval_identification import (
    addition_bounds, removal_bounds, quorum_classification,
    coupled_quorum_classification, robust_coupled_quorum_classification,
    minimum_relaxation_budget,
)

SEED=20260914
W=0.35
SHIFTS=[0.0,0.25,0.50,1.0,2.0]
N=10_000
M=8
K=5
Q=1
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'


def local_episode(direction: str, boundary: float):
    return (boundary,boundary+1.0) if direction=='addition' else (boundary-1.0,boundary)


def one_run(mult: float):
    rng=random.Random(SEED+int(round(mult*10000))+44117)
    sep_amb=rob_amb=rob_err=0
    strict_infeasible=strict_amb=strict_err=0
    strict_resolved=0
    mid_err=0
    qmins={str(i):0 for i in range(M+1)}
    candidate_evals=[]
    true_positive=0

    for _ in range(N):
        direction='addition' if rng.random()<0.5 else 'removal'
        theta=rng.uniform(0.15,0.65)
        contaminated=rng.randrange(M)
        brackets=[]; delays=[]; episodes=[]; latent=[]; midpoint=[]
        for j in range(M):
            alpha=0.0
            beta=W*(0.10+0.20*j/(M-1))
            delta=rng.uniform(alpha,beta)
            if mult>0 and j==contaminated:
                delta += mult*W
            a=theta+delta
            qpos=rng.random()
            l=a-qpos*W; u=l+W
            boundary=a+rng.uniform(-0.35,0.35)
            s,e=local_episode(direction,boundary)
            truth=(a>boundary) if direction=='addition' else (a<boundary)
            ahat=(l+u)/2.0
            mtruth=(ahat>boundary) if direction=='addition' else (ahat<boundary)
            brackets.append((l,u)); delays.append((alpha,beta)); episodes.append((s,e))
            latent.append(truth); midpoint.append(mtruth)

        true_quorum=sum(latent)>=K
        true_positive += true_quorum
        mid_err += (sum(midpoint)>=K) != true_quorum
        local_bounds=[
            addition_bounds(l,u,s,e) if direction=='addition' else removal_bounds(l,u,s,e)
            for (l,u),(s,e) in zip(brackets,episodes)
        ]
        sep=quorum_classification(local_bounds,K,0.0)
        sep_amb += sep=='quorum_ambiguous'

        qmin=minimum_relaxation_budget(brackets,delays)
        qmins[str(qmin)]+=1

        robust=robust_coupled_quorum_classification(direction,brackets,delays,episodes,K,Q,0.0)
        candidate_evals.append(robust.feasible_theta_candidates)
        if robust.classification=='quorum_ambiguous':
            rob_amb+=1
        else:
            pred=robust.classification=='quorum_confirmed'
            rob_err += pred!=true_quorum

        try:
            strict=coupled_quorum_classification(direction,brackets,delays,episodes,K,0.0)
        except ValueError:
            strict_infeasible+=1
        else:
            if strict.classification=='quorum_ambiguous':
                strict_amb+=1
            else:
                strict_resolved+=1
                pred=strict.classification=='quorum_confirmed'
                strict_err += pred!=true_quorum

    return {
        'shift_in_bracket_widths':mult,
        'n_events':N,
        'sources_per_event':M,
        'quorum_k':K,
        'robust_q':Q,
        'separable_ambiguous_pct':100*sep_amb/N,
        'robust_ambiguous_pct':100*rob_amb/N,
        'robust_ambiguity_reduction_pp':100*(sep_amb-rob_amb)/N,
        'robust_resolved_errors':rob_err,
        'strict_infeasible_pct':100*strict_infeasible/N,
        'strict_feasible_pct':100*(N-strict_infeasible)/N,
        'strict_ambiguous_pct_all_events':100*strict_amb/N,
        'strict_resolved_pct_all_events':100*strict_resolved/N,
        'strict_resolved_errors':strict_err,
        'strict_wrong_resolved_pct_all_events':100*strict_err/N,
        'strict_wrong_resolved_pct_of_resolved':100*strict_err/strict_resolved if strict_resolved else 0.0,
        'midpoint_quorum_error_pct':100*mid_err/N,
        'minimum_relaxation_budget_counts':qmins,
        'mean_feasible_theta_candidates_q1':sum(candidate_evals)/len(candidate_evals),
        'max_feasible_theta_candidates_q1':max(candidate_evals),
        'true_quorum_positive_pct':100*true_positive/N,
    }


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[one_run(x) for x in SHIFTS]
    csvp=OUT/'synthetic_robust_coupling_stress.csv'
    # flatten qmin counts out of CSV for readability
    flat=[]
    for r in rows:
        x={k:v for k,v in r.items() if k!='minimum_relaxation_budget_counts'}
        for q,n in r['minimum_relaxation_budget_counts'].items(): x[f'qmin_{q}_count']=n
        flat.append(x)
    with csvp.open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=list(flat[0].keys())); wr.writeheader(); wr.writerows(flat)
    summary={
        'seed':SEED,'n_events_per_shift':N,'sources_per_event':M,'quorum_k':K,
        'bracket_width':W,'robust_q':Q,
        'generator':{
            'shared_event':'one latent theta per event',
            'valid_constraints':'seven sources draw delay inside their stated envelope',
            'contaminated_constraint':'one source adds shift*w to a delay drawn inside its stated envelope; its local transition bracket remains valid',
            'local_bracket':'width w; random placement conditional on containing the source-local transition',
            'decision_boundary':'source-local threshold boundary is A_j + Uniform(-0.35,0.35)',
            'interpretation':'coupling-misspecification stress test only; not calibrated to Internet timing or contamination prevalence',
        },
        'rows':rows,
        'all_robust_resolved_decisions_correct':all(r['robust_resolved_errors']==0 for r in rows),
        'strict_model_can_be_feasible_and_wrong':any(r['strict_resolved_errors']>0 for r in rows[1:]),
    }
    (OUT/'synthetic_robust_coupling_stress.summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__': main()
