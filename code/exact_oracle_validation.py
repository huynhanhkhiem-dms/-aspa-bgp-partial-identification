#!/usr/bin/env python3
"""Implementation-independent exhaustive-oracle audit for the robust count set.

For small randomized problems, this script enumerates every allowed identity
set of relaxed coupling constraints.  The oracle reimplements source-local
duration geometry, conditional transition intersections, strict theta cells,
and binary contribution enumeration locally.  It imports only the two
production routines under test: the robust count-set function and the direct
robust-extrema evaluator.
"""
from __future__ import annotations
import itertools, json, random
from pathlib import Path
from robust_oracle_common import local_bounds, cond_interval, vals, source_theta_interval
from interval_identification import robust_coupled_quorum_count_set, robust_coupled_quorum_classification

SEED=20260915
N=30_000
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'output'
EPS=1e-12


def strict_count_set(direction,bs,ds,eps,indices,tau):
    if not indices:
        return {0}
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
        return set()
    pts=sorted(set(x for x in breaks if tl-EPS<=x<=tu+EPS) | {tl,tu})
    cand=set(pts)
    cand.update((x+y)/2 for x,y in zip(pts,pts[1:]) if y>x+EPS)
    out=set()
    for theta in cand:
        cur={0}; feasible=True
        for i in indices:
            l,u=bs[i]; a,b=ds[i]; s,e=eps[i]
            try:
                il,iu=cond_interval(l,u,a,b,theta)
            except ValueError:
                feasible=False; break
            lo,hi=local_bounds(direction,il,iu,s,e)
            cur={x+z for x in cur for z in vals(lo,hi,tau)}
        if feasible:
            out.update(cur)
    return out


def oracle(direction,bs,ds,eps,q,tau):
    m=len(bs)
    local=[local_bounds(direction,*bs[i],*eps[i]) for i in range(m)]
    total=set()
    for r in range(q+1):
        for relaxed_tuple in itertools.combinations(range(m),r):
            relaxed=set(relaxed_tuple); inside=[i for i in range(m) if i not in relaxed]
            strict=strict_count_set(direction,bs,ds,eps,inside,tau)
            if not strict:
                continue
            localset={0}
            for i in relaxed:
                localset={x+z for x in localset for z in vals(*local[i],tau)}
            total.update(a+b for a in strict for b in localset)
    return tuple(sorted(total))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rng=random.Random(SEED)
    matched=feasible=infeasible=0
    extrema_matched=0
    mismatch_examples=[]
    extrema_mismatch_examples=[]
    by_m={str(m):{'n':0,'matched':0,'feasible':0,'infeasible':0} for m in range(2,6)}
    for case in range(N):
        m=rng.randint(2,5); q=rng.randint(0,m); tau=rng.uniform(0.0,0.30)
        direction='addition' if rng.random()<0.5 else 'removal'
        bs=[]; ds=[]; eps=[]
        for _j in range(m):
            l=rng.uniform(-0.6,1.0); u=l+rng.uniform(0.03,0.9)
            a=rng.uniform(-0.25,0.25); b=a+rng.uniform(0.01,0.55)
            s=rng.uniform(-0.7,1.0); e=s+rng.uniform(0.08,1.25)
            bs.append((l,u)); ds.append((a,b)); eps.append((s,e))
        expected=oracle(direction,bs,ds,eps,q,tau)
        try:
            got=robust_coupled_quorum_count_set(direction,bs,ds,eps,q,tau)
        except ValueError:
            got=tuple()
        ok=(got==expected)
        # Independently audit the O(M^2) direct extrema path against the
        # oracle count-set extrema, rather than only against the production DP.
        try:
            direct=robust_coupled_quorum_classification(direction,bs,ds,eps,1,q,tau)
            got_extrema=(direct.count_lower,direct.count_upper)
        except ValueError:
            got_extrema=None
        expected_extrema=(min(expected),max(expected)) if expected else None
        extrema_ok=(got_extrema==expected_extrema)
        extrema_matched+=int(extrema_ok)
        matched+=int(ok); by_m[str(m)]['n']+=1; by_m[str(m)]['matched']+=int(ok)
        if expected:
            feasible+=1; by_m[str(m)]['feasible']+=1
        else:
            infeasible+=1; by_m[str(m)]['infeasible']+=1
        if not ok and len(mismatch_examples)<3:
            mismatch_examples.append({'case':case,'m':m,'q':q,'tau':tau,'direction':direction,
                                      'oracle':expected,'implementation':got})
        if not extrema_ok and len(extrema_mismatch_examples)<3:
            extrema_mismatch_examples.append({'case':case,'m':m,'q':q,'tau':tau,'direction':direction,
                                              'oracle_extrema':expected_extrema,'direct_extrema':got_extrema})
    summary={
        'seed':SEED,'n_instances':N,'m_range':[2,5],'q_range':[0,5],'q_sampling':'uniform on 0..M per instance',
        'feasible_instances':feasible,'infeasible_instances':infeasible,
        'match_count':matched,'mismatch_count':N-matched,
        'extrema_match_count':extrema_matched,'extrema_mismatch_count':N-extrema_matched,
        'all_instances_match':matched==N and extrema_matched==N,'by_m':by_m,
        'mismatch_examples':mismatch_examples,
        'extrema_mismatch_examples':extrema_mismatch_examples,
        'oracle_description':'explicit relaxed-identity enumeration with independently reimplemented local duration geometry, conditional intersections, theta grid, and binary contribution enumeration',
        'production_imports':['robust_coupled_quorum_count_set','robust_coupled_quorum_classification'],
    }
    (OUT/'exact_oracle_validation.summary.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))
    if matched!=N or extrema_matched!=N:
        raise SystemExit('EXACT_ORACLE_VALIDATION_FAILED')

if __name__=='__main__': main()
