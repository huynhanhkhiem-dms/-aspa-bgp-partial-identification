#!/usr/bin/env python3
"""Adversarially stratified q-sensitivity validation.

This validation is intentionally synthetic and does not estimate Internet
contamination prevalence. It strengthens the robustness audit in two ways:
(1) the misspecified coupling source is cycled through every source identity
and both displacement signs rather than sampled at random; and
(2) one- and two-contaminated-source regimes are compared with prespecified
q values. When q is at least the number of invalid coupling constraints, any
resolved robust decision should agree with latent truth; using too small q is
reported as a misspecification diagnostic rather than silently tuned away.
"""
from __future__ import annotations
import json, random
from pathlib import Path
from interval_identification import robust_coupled_quorum_classification

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'
SEED=20260914
W=0.35
M=8
K=5
N_PER_STRATUM=400
SHIFTS=(0.5,1.0)


def local_episode(direction,boundary):
    return (boundary,boundary+1.0) if direction=='addition' else (boundary-1.0,boundary)


def generate_event(rng, contaminated, sign, shift):
    direction='addition' if rng.random()<0.5 else 'removal'
    theta=rng.uniform(0.15,0.65)
    brackets=[]; delays=[]; episodes=[]; latent=[]
    contaminated=set(contaminated)
    for j in range(M):
        alpha=0.0
        beta=W*(0.10+0.20*j/(M-1))
        delta=rng.uniform(alpha,beta)
        if j in contaminated:
            delta += sign*shift*W
        a=theta+delta
        qpos=rng.random(); l=a-qpos*W; u=l+W
        boundary=a+rng.uniform(-0.35,0.35)
        s,e=local_episode(direction,boundary)
        truth=(a>boundary) if direction=='addition' else (a<boundary)
        brackets.append((l,u)); delays.append((alpha,beta)); episodes.append((s,e)); latent.append(truth)
    return direction,brackets,delays,episodes,(sum(latent)>=K)


def classify(event,q):
    direction,brackets,delays,episodes,truth=event
    try:
        r=robust_coupled_quorum_classification(direction,brackets,delays,episodes,K,q,0.0)
    except ValueError:
        return 'infeasible',False
    if r.classification=='quorum_ambiguous': return 'ambiguous',False
    pred=r.classification=='quorum_confirmed'
    return 'resolved',pred!=truth


def single_contamination():
    rows=[]
    for shift in SHIFTS:
      for sign in (-1,1):
       for src in range(M):
        rng=random.Random(SEED + int(shift*1000)*100 + (sign+1)*17 + src*7919)
        stats={q:{'n':0,'infeasible':0,'ambiguous':0,'resolved':0,'errors':0} for q in (0,1,2)}
        for _ in range(N_PER_STRATUM):
            ev=generate_event(rng,[src],sign,shift)
            for q in stats:
                status,err=classify(ev,q); d=stats[q]; d['n']+=1; d[status]+=1; d['errors']+=int(err)
        rows.append({'shift':shift,'sign':sign,'source':src,'q':stats})
    return rows


def double_contamination():
    # Balanced deterministic source pairs spanning low/high delay envelopes.
    pairs=((0,1),(0,7),(2,5),(3,4))
    rows=[]
    for shift in SHIFTS:
      for sign in (-1,1):
       for pair in pairs:
        rng=random.Random(SEED + 500000 + int(shift*1000)*100 + (sign+1)*31 + pair[0]*101 + pair[1]*1009)
        stats={q:{'n':0,'infeasible':0,'ambiguous':0,'resolved':0,'errors':0} for q in (1,2,3)}
        for _ in range(N_PER_STRATUM):
            ev=generate_event(rng,pair,sign,shift)
            for q in stats:
                status,err=classify(ev,q); d=stats[q]; d['n']+=1; d[status]+=1; d['errors']+=int(err)
        rows.append({'shift':shift,'sign':sign,'sources':pair,'q':stats})
    return rows


def aggregate(rows,qs):
    out={q:{'n':0,'infeasible':0,'ambiguous':0,'resolved':0,'errors':0} for q in qs}
    for row in rows:
        for q in qs:
            d=row['q'][q]; a=out[q]
            for k in a: a[k]+=d[k]
    for q,a in out.items():
        a['resolved_error_pct']=100*a['errors']/a['resolved'] if a['resolved'] else 0.0
        a['ambiguous_pct']=100*a['ambiguous']/a['n']
        a['infeasible_pct']=100*a['infeasible']/a['n']
    return out


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    s=single_contamination(); d=double_contamination()
    sa=aggregate(s,(0,1,2)); da=aggregate(d,(1,2,3))
    result={
      'seed':SEED,'M':M,'k':K,'bracket_width':W,'events_per_stratum':N_PER_STRATUM,'shifts':SHIFTS,
      'design':'all eight single-contamination identities x both displacement signs; selected balanced two-source contamination pairs x both signs',
      'interpretation':'synthetic assumption stress test; q is prespecified/sensitivity-indexed, never selected after viewing the desired label',
      'single_contamination':{'strata':s,'aggregate':sa},
      'double_contamination':{'strata':d,'aggregate':da},
      'checks':{
        'q1_zero_resolved_errors_when_one_constraint_invalid':sa[1]['errors']==0,
        'q2_zero_resolved_errors_when_one_constraint_invalid':sa[2]['errors']==0,
        'q2_zero_resolved_errors_when_two_constraints_invalid':da[2]['errors']==0,
        'q3_zero_resolved_errors_when_two_constraints_invalid':da[3]['errors']==0,
      }
    }
    p=OUT/'adversarial_q_sensitivity.summary.json'
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'single_aggregate':sa,'double_aggregate':da,'checks':result['checks']},indent=2,sort_keys=True))

if __name__=='__main__': main()
