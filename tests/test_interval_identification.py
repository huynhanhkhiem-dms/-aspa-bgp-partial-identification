import unittest
from interval_identification import (
    DurationBounds, addition_bounds, removal_bounds, guarded,
    prevalence_bounds, total_duration_bounds, width_bound_holds,
    exceedance_fraction_bounds, quorum_count_bounds, quorum_classification,
    point_observation_classification,
)


class IntervalIdentificationTests(unittest.TestCase):
    def test_addition_sharp_bounds_match_dense_enumeration(self):
        l,u,s,e = 4.0,8.0,2.0,10.0
        b = addition_bounds(l,u,s,e)
        vals=[max(0.0,min(e,l+(u-l)*i/10000)-s) for i in range(10001)]
        self.assertAlmostEqual(b.lower,min(vals)); self.assertAlmostEqual(b.upper,max(vals))
        self.assertEqual(b.classification,"definite_gap")

    def test_addition_ambiguous(self):
        b=addition_bounds(1,5,3,9)
        self.assertEqual((b.lower,b.upper),(0.0,2.0)); self.assertEqual(b.classification,"timing_ambiguous")

    def test_removal_sharp_bounds_match_dense_enumeration(self):
        l,u,s,e = 4.0,8.0,2.0,10.0
        b = removal_bounds(l,u,s,e)
        vals=[max(0.0,e-max(s,l+(u-l)*i/10000)) for i in range(10001)]
        self.assertAlmostEqual(b.lower,min(vals)); self.assertAlmostEqual(b.upper,max(vals))
        self.assertEqual(b.classification,"definite_gap")

    def test_removal_ambiguous(self):
        b=removal_bounds(4,12,2,10)
        self.assertEqual((b.lower,b.upper),(0.0,6.0)); self.assertEqual(b.classification,"timing_ambiguous")

    def test_guard(self):
        b=guarded(addition_bounds(6,8,2,10),1)
        self.assertEqual((b.lower,b.upper),(2.0,4.0))

    def test_width_bound(self):
        for b,w,ep in [
            (addition_bounds(4,8,2,10),4,8),
            (removal_bounds(4,8,2,10),4,8),
            (addition_bounds(1,9,5,6),8,1),
            (removal_bounds(1,9,5,6),8,1),
        ]:
            self.assertTrue(width_bound_holds(b,w,ep))

    def test_refinement_narrows_addition(self):
        outer=addition_bounds(2,9,3,10); inner=addition_bounds(4,7,3,10)
        self.assertGreaterEqual(inner.lower,outer.lower); self.assertLessEqual(inner.upper,outer.upper)

    def test_refinement_narrows_removal(self):
        outer=removal_bounds(2,9,3,10); inner=removal_bounds(4,7,3,10)
        self.assertGreaterEqual(inner.lower,outer.lower); self.assertLessEqual(inner.upper,outer.upper)

    def test_aggregate_prevalence_and_total_duration(self):
        xs=[DurationBounds(2,4),DurationBounds(0,3),DurationBounds(0,0),DurationBounds(1,1)]
        self.assertEqual(prevalence_bounds(xs),(0.5,0.75))
        self.assertEqual(total_duration_bounds(xs),DurationBounds(3,8))

if __name__ == '__main__': unittest.main()

class ThresholdAndQuorumTests(unittest.TestCase):
    def test_exceedance_envelope(self):
        xs=[DurationBounds(2,4),DurationBounds(0,3),DurationBounds(0,0),DurationBounds(1,1)]
        self.assertEqual(exceedance_fraction_bounds(xs,0),(0.5,0.75))
        self.assertEqual(exceedance_fraction_bounds(xs,1),(0.25,0.5))
        self.assertEqual(exceedance_fraction_bounds(xs,3),(0.0,0.25))

    def test_quorum_classification(self):
        xs=[DurationBounds(2,3),DurationBounds(1,2),DurationBounds(0,4),DurationBounds(0,0)]
        self.assertEqual(quorum_count_bounds(xs,0),(2,3))
        self.assertEqual(quorum_classification(xs,2,0),"quorum_confirmed")
        self.assertEqual(quorum_classification(xs,3,0),"quorum_ambiguous")
        self.assertEqual(quorum_classification(xs,4,0),"quorum_ruled_out")

    def test_thresholded_quorum(self):
        xs=[DurationBounds(2,5),DurationBounds(0,4),DurationBounds(3,3)]
        self.assertEqual(quorum_count_bounds(xs,2.5),(1,3))
        self.assertEqual(quorum_classification(xs,2,2.5),"quorum_ambiguous")


class PointObservationTests(unittest.TestCase):
    def test_addition_point_regions(self):
        self.assertEqual(point_observation_classification("addition",4,8,3),"definite_gap")
        self.assertEqual(point_observation_classification("addition",4,8,6),"timing_ambiguous")
        self.assertEqual(point_observation_classification("addition",4,8,8),"no_gap")

    def test_removal_point_regions(self):
        self.assertEqual(point_observation_classification("removal",4,8,3),"no_gap")
        self.assertEqual(point_observation_classification("removal",4,8,6),"timing_ambiguous")
        self.assertEqual(point_observation_classification("removal",4,8,8),"definite_gap")


def test_zero_length_episode_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        addition_bounds(1, 2, 3, 3)
    with pytest.raises(ValueError):
        removal_bounds(1, 2, 3, 3)

class CoupledIdentificationTests(unittest.TestCase):
    def test_shared_transition_interval_and_tension(self):
        from interval_identification import shared_transition_interval, shared_transition_tension
        bs=[(4,7),(5,8),(6,9)]
        ds=[(0,2),(1,3),(2,4)]
        self.assertEqual(shared_transition_interval(bs,ds),(2,7))
        self.assertEqual(shared_transition_tension(bs,ds),0.0)
        bad_bs=[(0,1),(10,11)]
        bad_ds=[(0,1),(0,1)]
        self.assertGreater(shared_transition_tension(bad_bs,bad_ds),0)
        with self.assertRaises(ValueError):
            shared_transition_interval(bad_bs,bad_ds)

    def test_conditional_interval(self):
        from interval_identification import conditional_transition_interval
        self.assertEqual(conditional_transition_interval(4,8,1,3,5),(6,8))

    def test_coupling_never_reverses_separable_resolved_label(self):
        from interval_identification import coupled_quorum_classification
        bs=[(4,8),(5,9),(4,7),(6,10),(5,8)]
        ds=[(0,2)]*5
        eps=[(3,12)]*5
        local=[addition_bounds(l,u,s,e) for (l,u),(s,e) in zip(bs,eps)]
        sep=quorum_classification(local,3,0)
        coup=coupled_quorum_classification('addition',bs,ds,eps,3,0).classification
        if sep!='quorum_ambiguous':
            self.assertEqual(coup,sep)

    def test_coupled_addition_matches_dense_shared_theta_enumeration(self):
        from interval_identification import coupled_quorum_classification, shared_transition_interval, conditional_transition_interval
        bs=[(0.30,0.60),(0.32,0.62),(0.28,0.58)]
        ds=[(0.00,0.10),(0.02,0.12),(0.01,0.11)]
        eps=[(0.40,0.90),(0.45,0.90),(0.42,0.90)]
        out=coupled_quorum_classification('addition',bs,ds,eps,2,0)
        tl,tu=shared_transition_interval(bs,ds)
        min_forced=99; max_possible=-1
        for z in range(2001):
            th=tl+(tu-tl)*z/2000
            forced=0; possible=0
            for (l,u),(a,b),(s,e) in zip(bs,ds,eps):
                lo,hi=conditional_transition_interval(l,u,a,b,th)
                bb=addition_bounds(lo,hi,s,e)
                forced += bb.lower>0
                possible += bb.upper>0
            min_forced=min(min_forced,forced); max_possible=max(max_possible,possible)
        self.assertEqual((out.count_lower,out.count_upper),(min_forced,max_possible))

    def test_coupled_removal_matches_dense_shared_theta_enumeration(self):
        from interval_identification import coupled_quorum_classification, shared_transition_interval, conditional_transition_interval
        bs=[(0.30,0.60),(0.32,0.62),(0.28,0.58)]
        ds=[(0.00,0.10),(0.02,0.12),(0.01,0.11)]
        eps=[(0.10,0.50),(0.10,0.55),(0.10,0.52)]
        out=coupled_quorum_classification('removal',bs,ds,eps,2,0)
        tl,tu=shared_transition_interval(bs,ds)
        min_forced=99; max_possible=-1
        for z in range(2001):
            th=tl+(tu-tl)*z/2000
            forced=0; possible=0
            for (l,u),(a,b),(s,e) in zip(bs,ds,eps):
                lo,hi=conditional_transition_interval(l,u,a,b,th)
                bb=removal_bounds(lo,hi,s,e)
                forced += bb.lower>0
                possible += bb.upper>0
            min_forced=min(min_forced,forced); max_possible=max(max_possible,possible)
        self.assertEqual((out.count_lower,out.count_upper),(min_forced,max_possible))


def test_uniform_feasibility_slack_is_half_tension():
    from interval_identification import shared_transition_tension, uniform_feasibility_slack
    brackets=[(1.0,1.2),(1.5,1.7)]
    delays=[(0.0,0.1),(0.0,0.1)]
    d=shared_transition_tension(brackets,delays)
    assert abs(d-0.2)<1e-12
    assert abs(uniform_feasibility_slack(brackets,delays)-0.1)<1e-12


def test_point_resolution_margin():
    from interval_identification import point_resolution_margin
    assert point_resolution_margin(0.0,10.0,6.0)==4.0
    assert point_resolution_margin(0.0,10.0,0.0)==0.0
    assert point_resolution_margin(0.0,10.0,10.0)==0.0

class RobustCoupledIdentificationTests(unittest.TestCase):
    def _enumerate_relaxed_subsets(self, direction, bs, ds, eps, q, threshold=0.0):
        from itertools import combinations
        from interval_identification import (
            coupled_quorum_classification, addition_bounds, removal_bounds,
            quorum_count_bounds,
        )
        m=len(bs); lows=[]; highs=[]
        local=[(addition_bounds(*b,*ep) if direction=='addition' else removal_bounds(*b,*ep))
               for b,ep in zip(bs,eps)]
        for r in range(q+1):
            for out_tuple in combinations(range(m),r):
                outset=set(out_tuple); in_idx=[i for i in range(m) if i not in outset]
                out_idx=sorted(outset)
                out_lo=sum(local[i].lower>threshold for i in out_idx)
                out_hi=sum(local[i].upper>threshold for i in out_idx)
                if not in_idx:
                    in_lo=in_hi=0
                else:
                    ib=[bs[i] for i in in_idx]; idl=[ds[i] for i in in_idx]; ie=[eps[i] for i in in_idx]
                    try:
                        rr=coupled_quorum_classification(direction,ib,idl,ie,1,threshold)
                    except ValueError:
                        continue
                    in_lo=rr.count_lower; in_hi=rr.count_upper
                lows.append(out_lo+in_lo); highs.append(out_hi+in_hi)
        if not lows:
            raise ValueError('no feasible relaxed subset')
        return min(lows),max(highs)

    def test_q_zero_recovers_strict_coupling(self):
        from interval_identification import coupled_quorum_classification, robust_coupled_quorum_classification
        bs=[(0.30,0.60),(0.32,0.62),(0.28,0.58),(0.31,0.61)]
        ds=[(0.00,0.10),(0.02,0.12),(0.01,0.11),(0.00,0.09)]
        eps=[(0.40,0.90),(0.45,0.90),(0.42,0.90),(0.44,0.90)]
        strict=coupled_quorum_classification('addition',bs,ds,eps,3,0)
        robust=robust_coupled_quorum_classification('addition',bs,ds,eps,3,0,0)
        self.assertEqual((robust.count_lower,robust.count_upper,robust.classification),
                         (strict.count_lower,strict.count_upper,strict.classification))

    def test_q_m_recovers_separable(self):
        from interval_identification import robust_coupled_quorum_classification, addition_bounds, quorum_count_bounds
        bs=[(0.10,0.60),(0.20,0.70),(0.30,0.80)]
        ds=[(0.0,0.05)]*3
        eps=[(0.35,1.0),(0.50,1.0),(0.65,1.0)]
        local=[addition_bounds(*b,*ep) for b,ep in zip(bs,eps)]
        sep=quorum_count_bounds(local,0)
        robust=robust_coupled_quorum_classification('addition',bs,ds,eps,2,3,0)
        self.assertEqual((robust.count_lower,robust.count_upper),sep)

    def test_robust_addition_matches_subset_enumeration(self):
        from interval_identification import robust_coupled_quorum_classification
        bs=[(0.30,0.62),(0.34,0.66),(0.26,0.58),(0.52,0.84)]
        ds=[(0.00,0.08),(0.01,0.10),(0.00,0.09),(0.00,0.05)]
        eps=[(0.41,0.95),(0.48,0.95),(0.39,0.95),(0.60,0.95)]
        exact=self._enumerate_relaxed_subsets('addition',bs,ds,eps,1,0)
        out=robust_coupled_quorum_classification('addition',bs,ds,eps,3,1,0)
        self.assertEqual((out.count_lower,out.count_upper),exact)
        self.assertLessEqual(out.feasible_theta_candidates,8*len(bs)-1)

    def test_robust_removal_matches_subset_enumeration(self):
        from interval_identification import robust_coupled_quorum_classification
        bs=[(0.30,0.62),(0.34,0.66),(0.26,0.58),(0.52,0.84)]
        ds=[(0.00,0.08),(0.01,0.10),(0.00,0.09),(0.00,0.05)]
        eps=[(0.05,0.44),(0.05,0.50),(0.05,0.42),(0.05,0.62)]
        exact=self._enumerate_relaxed_subsets('removal',bs,ds,eps,1,0)
        out=robust_coupled_quorum_classification('removal',bs,ds,eps,3,1,0)
        self.assertEqual((out.count_lower,out.count_upper),exact)
        self.assertLessEqual(out.feasible_theta_candidates,8*len(bs)-1)

    def test_minimum_relaxation_budget(self):
        from interval_identification import minimum_relaxation_budget, q_relaxed_transition_components
        bs=[(0.00,0.10),(0.02,0.12),(0.80,0.90)]
        ds=[(0.0,0.02)]*3
        self.assertEqual(minimum_relaxation_budget(bs,ds),1)
        self.assertEqual(q_relaxed_transition_components(bs,ds,0),[])
        self.assertTrue(q_relaxed_transition_components(bs,ds,1))

def test_robust_exact_randomized_against_subset_enumeration():
    import random
    from itertools import combinations
    from interval_identification import (
        robust_coupled_quorum_classification, coupled_quorum_classification,
        addition_bounds, removal_bounds,
    )
    rng=random.Random(99173)
    for direction in ('addition','removal'):
        for _ in range(20):
            m=4; q=rng.randrange(0,3); k=rng.randrange(1,m+1); threshold=rng.uniform(0.0,0.15)
            theta=rng.uniform(0.25,0.55)
            bs=[]; ds=[]; eps=[]
            for j in range(m):
                a=0.0; b=rng.uniform(0.03,0.12)
                aj=theta+rng.uniform(a,b)
                w=rng.uniform(0.16,0.34)
                pos=rng.random(); l=aj-pos*w; u=l+w
                boundary=aj+rng.uniform(-0.20,0.20)
                ep=(boundary,boundary+0.8) if direction=='addition' else (boundary-0.8,boundary)
                bs.append((l,u)); ds.append((a,b)); eps.append(ep)
            # Deliberately perturb at most one delay relation in half the cases
            # while preserving every source-local transition bracket.
            if q>=1 and rng.random()<0.5:
                j=rng.randrange(m)
                l,u=bs[j]
                bs[j]=(l+0.08,u+0.08)

            got=robust_coupled_quorum_classification(direction,bs,ds,eps,k,q,threshold)
            local=[addition_bounds(*b,*ep) if direction=='addition' else removal_bounds(*b,*ep)
                   for b,ep in zip(bs,eps)]
            lows=[]; highs=[]
            for r in range(q+1):
                for out in combinations(range(m),r):
                    out=set(out); inside=[i for i in range(m) if i not in out]
                    lo=sum(local[i].lower>threshold for i in out)
                    hi=sum(local[i].upper>threshold for i in out)
                    if inside:
                        try:
                            rr=coupled_quorum_classification(
                                direction,[bs[i] for i in inside],[ds[i] for i in inside],
                                [eps[i] for i in inside],1,threshold)
                        except ValueError:
                            continue
                        lo+=rr.count_lower; hi+=rr.count_upper
                    lows.append(lo); highs.append(hi)
            assert lows
            assert (got.count_lower,got.count_upper)==(min(lows),max(highs))

def test_common_state_support_not_sufficient_for_downstream_quorum():
    """Regression witness for Proposition 10 (support-only fusion insufficiency).

    Two instances have identical source-implied H_j intervals and identical
    BGP episodes, hence identical strict/q-relaxed common-time support, but
    different q=1 sharp downstream quorum bounds because a relaxed source
    retains different source-local transition evidence.
    """
    from interval_identification import (
        q_relaxed_transition_components,
        robust_coupled_quorum_classification,
    )
    episodes=[(0.5,2.0),(0.5,2.0)]
    a_brackets=[(0.0,1.0),(0.0,1.0)]
    a_delays=[(0.0,0.0),(0.0,0.0)]
    b_brackets=[(1.0,2.0),(0.0,1.0)]
    b_delays=[(1.0,1.0),(0.0,0.0)]

    assert q_relaxed_transition_components(a_brackets,a_delays,1)==[(0.0,1.0)]
    assert q_relaxed_transition_components(b_brackets,b_delays,1)==[(0.0,1.0)]

    a=robust_coupled_quorum_classification(
        'addition',a_brackets,a_delays,episodes,k=1,q=1,threshold=0.0)
    b=robust_coupled_quorum_classification(
        'addition',b_brackets,b_delays,episodes,k=1,q=1,threshold=0.0)
    assert (a.count_lower,a.count_upper)==(0,2)
    assert (b.count_lower,b.count_upper)==(1,2)
    assert a.classification=='quorum_ambiguous'
    assert b.classification=='quorum_confirmed'

def test_exact_robust_count_set_can_be_nonconvex_and_matches_envelope():
    """The exact attainable count set need not equal its sharp interval hull."""
    from interval_identification import (
        robust_coupled_quorum_count_set,
        robust_coupled_quorum_classification,
    )
    brackets=[(-0.5,1.0),(1.5,2.5),(-1.0,3.0),(-1.0,1.0)]
    delays=[(0.5,0.5),(0.5,0.5),(1.0,1.0),(1.0,1.0)]
    episodes=[(-0.5,2.5),(0.0,0.5),(1.0,1.5),(0.0,1.0)]
    exact=robust_coupled_quorum_count_set(
        'addition', brackets, delays, episodes, q=1, threshold=0.5)
    hull=robust_coupled_quorum_classification(
        'addition', brackets, delays, episodes, k=1, q=1, threshold=0.5)
    assert exact==(0,2)
    assert (hull.count_lower,hull.count_upper)==(0,2)
    assert 1 not in exact


def test_exact_robust_count_set_randomized_extrema_agree():
    """Independent exact-set DP and fast extrema evaluator agree on randomized cases."""
    import random
    from interval_identification import (
        robust_coupled_quorum_count_set,
        robust_coupled_quorum_classification,
    )
    rng=random.Random(20260915)
    checked=0
    for direction in ('addition','removal'):
        for _ in range(80):
            m=4; q=rng.randrange(0,3); threshold=rng.uniform(0.0,0.2)
            bs=[]; ds=[]; eps=[]
            for _j in range(m):
                l=rng.uniform(-0.5,0.8); u=l+rng.uniform(0.05,0.8)
                a=rng.uniform(-0.2,0.2); b=a+rng.uniform(0.02,0.5)
                s=rng.uniform(-0.5,0.8); e=s+rng.uniform(0.15,1.0)
                bs.append((l,u)); ds.append((a,b)); eps.append((s,e))
            try:
                exact=robust_coupled_quorum_count_set(direction,bs,ds,eps,q,threshold)
                fast=robust_coupled_quorum_classification(
                    direction,bs,ds,eps,k=2,q=q,threshold=threshold)
            except ValueError:
                continue
            assert exact
            assert (min(exact),max(exact))==(fast.count_lower,fast.count_upper)
            expected=('quorum_confirmed' if min(exact)>=2 else
                      'quorum_ruled_out' if max(exact)<2 else 'quorum_ambiguous')
            assert fast.classification==expected
            checked+=1
    assert checked>=40

def test_exact_robust_count_set_matches_relaxed_subset_enumeration():
    """Randomized exact-set check against explicit relaxed-subset enumeration."""
    import random
    from itertools import combinations
    from interval_identification import (
        robust_coupled_quorum_count_set,
        conditional_transition_interval,
        addition_bounds,
        removal_bounds,
    )

    def d_bounds(direction,l,u,s,e):
        return addition_bounds(l,u,s,e) if direction=='addition' else removal_bounds(l,u,s,e)

    def indicator_values(bounds,tau):
        lo=int(bounds.lower>tau); hi=int(bounds.upper>tau)
        return {lo} if lo==hi else {0,1}

    def strict_count_set(direction,bs,ds,eps,tau):
        hs=[(l-b,u-a) for (l,u),(a,b) in zip(bs,ds)]
        tl=max(x for x,_ in hs); tu=min(y for _,y in hs)
        if tl>tu+1e-12:
            return set()
        pts={tl,tu}
        for (l,u),(a,b),(s,e) in zip(bs,ds,eps):
            if tau<e-s:
                boundary=(s+tau) if direction=='addition' else (e-tau)
                pts.update((boundary-a,boundary-b))
        pts=sorted(x for x in pts if tl-1e-12<=x<=tu+1e-12)
        cand=set(pts)
        cand.update((x+y)/2 for x,y in zip(pts,pts[1:]) if y>x)
        out=set()
        for theta in cand:
            possible={0}
            try:
                for (l,u),(a,b),(s,e) in zip(bs,ds,eps):
                    cl,cu=conditional_transition_interval(l,u,a,b,theta)
                    z=indicator_values(d_bounds(direction,cl,cu,s,e),tau)
                    possible={x+y for x in possible for y in z}
            except ValueError:
                continue
            out.update(possible)
        return out

    rng=random.Random(20260916)
    for direction in ('addition','removal'):
        for _ in range(40):
            m=4; q=rng.randrange(0,3); tau=rng.uniform(0.0,0.2)
            bs=[]; ds=[]; eps=[]
            for _j in range(m):
                l=rng.uniform(-0.5,0.8); u=l+rng.uniform(0.05,0.8)
                a=rng.uniform(-0.2,0.2); b=a+rng.uniform(0.02,0.5)
                s=rng.uniform(-0.5,0.8); e=s+rng.uniform(0.15,1.0)
                bs.append((l,u)); ds.append((a,b)); eps.append((s,e))

            expected=set()
            local=[indicator_values(d_bounds(direction,*br,*ep),tau)
                   for br,ep in zip(bs,eps)]
            for r in range(q+1):
                for relaxed_tuple in combinations(range(m),r):
                    relaxed=set(relaxed_tuple)
                    inside=[i for i in range(m) if i not in relaxed]
                    strict={0} if not inside else strict_count_set(
                        direction,[bs[i] for i in inside],[ds[i] for i in inside],
                        [eps[i] for i in inside],tau)
                    if not strict:
                        continue
                    rcounts={0}
                    for i in relaxed:
                        rcounts={x+y for x in rcounts for y in local[i]}
                    expected.update(x+y for x in strict for y in rcounts)
            try:
                got=set(robust_coupled_quorum_count_set(direction,bs,ds,eps,q,tau))
            except ValueError:
                got=set()
            assert got==expected


def test_robust_q_envelope_nests_as_q_increases_on_fixed_instance():
    """Larger contamination budgets cannot create a sharper count hull."""
    from interval_identification import robust_coupled_quorum_classification
    direction='addition'
    brackets=[(0.1,0.45),(0.2,0.55),(0.3,0.65),(0.4,0.75)]
    delays=[(0.0,0.12),(0.0,0.14),(0.0,0.16),(0.0,0.18)]
    episodes=[(0.25,1.25),(0.35,1.35),(0.45,1.45),(0.55,1.55)]
    prev=None
    for q in range(5):
        r=robust_coupled_quorum_classification(direction,brackets,delays,episodes,2,q,0.0)
        cur=(r.count_lower,r.count_upper)
        if prev is not None:
            assert cur[0] <= prev[0]
            assert cur[1] >= prev[1]
        prev=cur


def test_q_equals_m_recovers_separable_count_bounds():
    from interval_identification import robust_coupled_quorum_classification
    direction='removal'
    brackets=[(0.0,0.4),(0.2,0.7),(0.6,1.0)]
    delays=[(0.0,0.1)]*3
    episodes=[(-0.2,0.5),(0.1,0.8),(0.4,1.2)]
    local=[removal_bounds(l,u,s,e) for (l,u),(s,e) in zip(brackets,episodes)]
    lo,hi=quorum_count_bounds(local,0.0)
    r=robust_coupled_quorum_classification(direction,brackets,delays,episodes,2,3,0.0)
    assert (r.count_lower,r.count_upper)==(lo,hi)


def test_conformal_q_budget_rank_rule_and_boundary():
    from interval_identification import conformal_q_budget
    # n=19, alpha=.10 => ceil(20*.9)=18: 18th order statistic.
    cal=[0]*10+[1]*7+[2]*2
    assert conformal_q_budget(cal,0.10,8)==2
    # Very high requested coverage with too little calibration falls back to M.
    assert conformal_q_budget([0,0,1],0.01,8)==8


def test_unweighted_extrema_equal_exact_count_set_extrema_randomized():
    import random
    from interval_identification import robust_coupled_quorum_classification, robust_coupled_quorum_count_set
    rng=random.Random(20260917)
    checked=0
    for _ in range(1000):
        m=rng.randint(2,6); q=rng.randint(0,m); tau=rng.uniform(0.0,0.25)
        direction='addition' if rng.random()<0.5 else 'removal'
        bs=[]; ds=[]; eps=[]
        for _j in range(m):
            l=rng.uniform(-0.5,1.0); u=l+rng.uniform(0.04,0.8)
            a=rng.uniform(-0.2,0.2); b=a+rng.uniform(0.01,0.45)
            s=rng.uniform(-0.6,0.9); e=s+rng.uniform(0.10,1.1)
            bs.append((l,u)); ds.append((a,b)); eps.append((s,e))
        try:
            cs=robust_coupled_quorum_count_set(direction,bs,ds,eps,q,tau)
            rr=robust_coupled_quorum_classification(direction,bs,ds,eps,1,q,tau)
        except ValueError:
            continue
        assert (rr.count_lower,rr.count_upper)==(min(cs),max(cs))
        checked+=1
    assert checked>700


def test_weighted_equal_weights_recover_unweighted_extrema():
    from interval_identification import robust_coupled_quorum_classification, robust_coupled_weighted_score_bounds
    bs=[(0.30,0.62),(0.34,0.66),(0.26,0.58),(0.52,0.84)]
    ds=[(0.00,0.08),(0.01,0.10),(0.00,0.09),(0.00,0.05)]
    eps=[(0.41,0.95),(0.48,0.95),(0.39,0.95),(0.60,0.95)]
    rr=robust_coupled_quorum_classification('addition',bs,ds,eps,3,1,0.0)
    wr=robust_coupled_weighted_score_bounds('addition',bs,ds,eps,[1,1,1,1],1,0.0)
    assert (wr.score_lower,wr.score_upper)==(rr.count_lower,rr.count_upper)
