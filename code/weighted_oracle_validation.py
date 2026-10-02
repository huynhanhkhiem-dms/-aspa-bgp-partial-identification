#!/usr/bin/env python3
"""Independent exhaustive audit of nonnegative weighted robust score extrema."""
from __future__ import annotations
import itertools, json, random
from pathlib import Path
from robust_oracle_common import local_bounds, cond_interval, source_theta_interval
from interval_identification import robust_coupled_weighted_score_bounds

SEED=20260916
N=20_000
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'
EPS=1e-12


def strict_weighted_extrema(direction,bs,ds,eps,weights,indices,tau):
    if not indices:
        return 0.0,0.0
    hs=[]; breaks=[]
    for i in indices:
        l,u=bs[i]; a,b=ds[i]; s,e=eps[i]
        hs.append(source_theta_interval(l,u,a,b))
        breaks.extend((l-b,u-a))
        if tau<e-s:
            boundary=(s+tau) if direction=='addition' else (e-tau)
            breaks.extend((boundary-a,boundary-b))
    tl=max(x for x,_ in hs); tu=min(y for _,y in hs)
    if tl>tu+EPS:
        raise ValueError('infeasible')
    pts=sorted(set(x for x in breaks if tl-EPS<=x<=tu+EPS)|{tl,tu})
    cand=set(pts); cand.update((x+y)/2 for x,y in zip(pts,pts[1:]) if y>x+EPS)
    glo=None; ghi=None
    for theta in cand:
        lo=hi=0.0; good=True
        for i in indices:
            l,u=bs[i]; a,b=ds[i]; s,e=eps[i]
            try: il,iu=cond_interval(l,u,a,b,theta)
            except ValueError: good=False; break
            dl,du=local_bounds(direction,il,iu,s,e)
            lo += weights[i]*int(dl>tau)
            hi += weights[i]*int(du>tau)
        if good:
            glo=lo if glo is None else min(glo,lo)
            ghi=hi if ghi is None else max(ghi,hi)
    if glo is None: raise ValueError('infeasible')
    return glo,ghi


def oracle(direction,bs,ds,eps,weights,q,tau):
    m=len(bs); locals_=[local_bounds(direction,*bs[i],*eps[i]) for i in range(m)]
    lows=[]; highs=[]
    for r in range(q+1):
        for relax_tuple in itertools.combinations(range(m),r):
            relax=set(relax_tuple); inside=[i for i in range(m) if i not in relax]
            try: slo,shi=strict_weighted_extrema(direction,bs,ds,eps,weights,inside,tau)
            except ValueError: continue
            llo=sum(weights[i]*int(locals_[i][0]>tau) for i in relax)
            lhi=sum(weights[i]*int(locals_[i][1]>tau) for i in relax)
            lows.append(slo+llo); highs.append(shi+lhi)
    if not lows: raise ValueError('infeasible')
    return min(lows),max(highs)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rng=random.Random(SEED); matched=0; infeasible=0; examples=[]
    for case in range(N):
        m=rng.randint(2,5); q=rng.randint(0,m); tau=rng.uniform(0,0.30)
        direction='addition' if rng.random()<0.5 else 'removal'
        bs=[]; ds=[]; eps=[]; weights=[rng.randint(0,5) for _ in range(m)]
        for _ in range(m):
            l=rng.uniform(-0.6,1.0); u=l+rng.uniform(0.03,0.9)
            a=rng.uniform(-0.25,0.25); b=a+rng.uniform(0.01,0.55)
            s=rng.uniform(-0.7,1.0); e=s+rng.uniform(0.08,1.25)
            bs.append((l,u)); ds.append((a,b)); eps.append((s,e))
        try: expected=oracle(direction,bs,ds,eps,weights,q,tau)
        except ValueError: expected=None
        try:
            got=robust_coupled_weighted_score_bounds(direction,bs,ds,eps,weights,q,tau)
            observed=(got.score_lower,got.score_upper)
        except ValueError: observed=None
        ok=(expected is None and observed is None) or (expected is not None and observed is not None and abs(expected[0]-observed[0])<1e-9 and abs(expected[1]-observed[1])<1e-9)
        matched += int(ok); infeasible += int(expected is None)
        if not ok and len(examples)<3: examples.append({'case':case,'expected':expected,'observed':observed})
    summary={'seed':SEED,'n_instances':N,'weights':[0,5],'q_sampling':'uniform on 0..M per instance','match_count':matched,'mismatch_count':N-matched,
             'infeasible_instances':infeasible,'all_instances_match':matched==N,'mismatch_examples':examples,
             'oracle_description':'relaxed-source identity enumeration with independent local geometry and strict theta-cell enumeration'}
    (OUT/'weighted_oracle_validation.summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2,sort_keys=True))
    if matched!=N: raise SystemExit('WEIGHTED_ORACLE_VALIDATION_FAILED')
if __name__=='__main__': main()
