#!/usr/bin/env python3
"""Cross-configuration latent-truth validation of robust coupled quorum bounds.

This deterministic stress grid broadens the main validation beyond a single
M=8, k=5 configuration.  It is an implementation/identification stress test,
not a model of Internet timing frequencies.
"""
from __future__ import annotations
import csv, json, math, random
from pathlib import Path
from interval_identification import (
    addition_bounds, removal_bounds, quorum_count_bounds,
    robust_coupled_quorum_classification,
)

SEED=20260915
MS=(4,8,16)
QS=(0,1,2)
WIDTHS=(0.10,0.35,0.60)
TAUS=(0.0,0.10,0.25)
N_PER_CELL=1000
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'


def episode(direction: str, boundary: float) -> tuple[float,float]:
    # Unit episode centered relative to the threshold boundary.  With this
    # parameterization, D>tau is determined by A versus boundary +/- tau.
    return (boundary,boundary+1.0) if direction=='addition' else (boundary-1.0,boundary)


def truth_positive(direction: str, a: float, s: float, e: float, tau: float) -> bool:
    d=max(0.0,min(e,a)-s) if direction=='addition' else max(0.0,e-max(s,a))
    return d>tau


def quorum_ks(m: int) -> tuple[int,...]:
    return tuple(sorted({math.ceil(m/3), math.ceil(m/2), math.ceil(2*m/3)}))


def run_cell(m: int, q: int, w: float, tau: float) -> list[dict]:
    # A cell-specific seed avoids order dependence and makes every cell exactly
    # reproducible in isolation.
    seed=SEED + 100000*m + 10000*q + int(round(1000*w)) + int(round(100*tau))
    rng=random.Random(seed)
    ks=quorum_ks(m)
    stats={k:{'sep_amb':0,'rob_amb':0,'sep_err':0,'rob_err':0,'n':0} for k in ks}

    for _ in range(N_PER_CELL):
        direction='addition' if rng.random()<0.5 else 'removal'
        theta=rng.uniform(0.20,0.80)
        bad=set(rng.sample(range(m),q)) if q else set()
        brackets=[]; delays=[]; episodes=[]; local_bounds=[]; truth=[]
        for j in range(m):
            # Stated source delay interval is intentionally heterogeneous.
            alpha=0.0
            beta=w*(0.10+0.20*j/max(1,m-1))
            stated_delta=rng.uniform(alpha,beta)
            true_delta=stated_delta
            if j in bad:
                # Violate this source-to-common-event constraint while keeping
                # the source-local transition bracket fully valid.
                true_delta += w*(0.70+0.30*rng.random())
            a=theta+true_delta
            pos=rng.random()
            l=a-pos*w; u=l+w
            # Keep the decision boundary near A so both resolved and ambiguous
            # cases occur across all widths and thresholds.
            boundary=a+rng.uniform(-0.45,0.45)
            s,e=episode(direction,boundary)
            b=(addition_bounds(l,u,s,e) if direction=='addition'
               else removal_bounds(l,u,s,e))
            brackets.append((l,u)); delays.append((alpha,beta)); episodes.append((s,e))
            local_bounds.append(b); truth.append(truth_positive(direction,a,s,e,tau))

        true_count=sum(truth)
        sep_lo,sep_hi=quorum_count_bounds(local_bounds,tau)
        # Count extrema do not depend on k, so compute the robust envelope once
        # per event and reuse it for all requested quorum thresholds.
        robust=robust_coupled_quorum_classification(
            direction,brackets,delays,episodes,1,q,tau)
        rob_lo,rob_hi=robust.count_lower,robust.count_upper
        for k in ks:
            true_q=true_count>=k
            sep=('quorum_confirmed' if sep_lo>=k else
                 'quorum_ruled_out' if sep_hi<k else 'quorum_ambiguous')
            rob=('quorum_confirmed' if rob_lo>=k else
                 'quorum_ruled_out' if rob_hi<k else 'quorum_ambiguous')
            st=stats[k]; st['n']+=1
            if sep=='quorum_ambiguous': st['sep_amb']+=1
            else: st['sep_err'] += ((sep=='quorum_confirmed') != true_q)
            if rob=='quorum_ambiguous': st['rob_amb']+=1
            else: st['rob_err'] += ((rob=='quorum_confirmed') != true_q)

    rows=[]
    for k,st in stats.items():
        n=st['n']
        sep=100*st['sep_amb']/n; rob=100*st['rob_amb']/n
        rows.append({
            'm_sources':m,'robust_q':q,'bracket_width':w,'threshold_tau':tau,
            'quorum_k':k,'n_events':n,
            'separable_ambiguous_pct':sep,
            'robust_ambiguous_pct':rob,
            'ambiguity_reduction_pp':sep-rob,
            'separable_resolved_errors':st['sep_err'],
            'robust_resolved_errors':st['rob_err'],
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    import os
    cells=[(m,q,w,tau) for m in MS for q in QS for w in WIDTHS for tau in TAUS]
    if os.environ.get('ASPA_NO_MP')=='1':
        chunks=[run_cell(*cell) for cell in cells]
    else:
        from multiprocessing import Pool
        with Pool(processes=min(5,len(cells))) as pool:
            chunks=pool.starmap(run_cell,cells)
    rows=[r for chunk in chunks for r in chunk]

    csvp=OUT/'robust_generalization_grid.csv'
    with csvp.open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    by_m=[]
    for m in MS:
        rr=[r for r in rows if r['m_sources']==m]
        events=len(QS)*len(WIDTHS)*len(TAUS)*N_PER_CELL
        decisions=sum(r['n_events'] for r in rr)
        by_m.append({
            'm_sources':m,
            'generated_events':events,
            'quorum_decisions':decisions,
            'mean_ambiguity_reduction_pp':sum(r['ambiguity_reduction_pp'] for r in rr)/len(rr),
            'max_ambiguity_reduction_pp':max(r['ambiguity_reduction_pp'] for r in rr),
            'robust_resolved_errors':sum(r['robust_resolved_errors'] for r in rr),
            'separable_resolved_errors':sum(r['separable_resolved_errors'] for r in rr),
        })
    summary={
        'seed':SEED,
        'm_values':list(MS),'q_values':list(QS),'bracket_widths':list(WIDTHS),
        'thresholds':list(TAUS),'events_per_geometry_cell':N_PER_CELL,
        'geometry_cells':len(MS)*len(QS)*len(WIDTHS)*len(TAUS),
        'generated_events':len(MS)*len(QS)*len(WIDTHS)*len(TAUS)*N_PER_CELL,
        'quorum_decisions':sum(r['n_events'] for r in rows),
        'reported_settings':len(rows),
        'by_m':by_m,
        'mean_ambiguity_reduction_pp':sum(r['ambiguity_reduction_pp'] for r in rows)/len(rows),
        'max_ambiguity_reduction_pp':max(r['ambiguity_reduction_pp'] for r in rows),
        'positive_reduction_settings':sum(r['ambiguity_reduction_pp']>1e-12 for r in rows),
        'unchanged_settings':sum(abs(r['ambiguity_reduction_pp'])<=1e-12 for r in rows),
        'all_robust_resolved_decisions_correct':all(r['robust_resolved_errors']==0 for r in rows),
        'all_separable_resolved_decisions_correct':all(r['separable_resolved_errors']==0 for r in rows),
        'robust_never_more_ambiguous_than_separable':all(r['robust_ambiguous_pct']<=r['separable_ambiguous_pct']+1e-12 for r in rows),
        'interpretation':'latent-truth implementation and structural-generalization stress test; not calibrated to Internet frequencies',
    }
    (OUT/'robust_generalization_grid.summary.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__': main()
