#!/usr/bin/env python3
"""Sharp identification of cross-plane gap duration under interval-censored timing.

For a covered BGP provider-edge episode [s,e), the RPKI transition time a is
known only through a declared closed analysis support [l,u]. Under the
single-transition model the functions below return the exact closed identified
hull; for raw endpoint conventions with the same closure they are fail-closed
outer bounds. Hidden reversals require separate modeling and are not repaired
by endpoint closure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


def _pos(x: float) -> float:
    return max(0.0, float(x))


@dataclass(frozen=True)
class DurationBounds:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower < 0 or self.upper < self.lower:
            raise ValueError("invalid duration bounds")

    @property
    def width(self) -> float:
        return self.upper - self.lower

    @property
    def classification(self) -> str:
        if self.lower > 0:
            return "definite_gap"
        if self.upper > 0:
            return "timing_ambiguous"
        return "no_gap"


def addition_bounds(l: float, u: float, s: float, e: float) -> DurationBounds:
    """Sharp bounds for Not Provider+ -> Provider+.

    Latent gap duration at transition time a is [min(e,a)-s]_+.
    """
    if l > u:
        raise ValueError("transition lower bound exceeds upper bound")
    if s >= e:
        raise ValueError("BGP episode must have positive covered duration")
    lo = _pos(min(e, l) - s)
    hi = _pos(min(e, u) - s)
    return DurationBounds(lo, hi)


def removal_bounds(l: float, u: float, s: float, e: float) -> DurationBounds:
    """Sharp bounds for Provider+ -> Not Provider+.

    Latent gap duration at transition time a is [e-max(s,a)]_+.
    """
    if l > u:
        raise ValueError("transition lower bound exceeds upper bound")
    if s >= e:
        raise ValueError("BGP episode must have positive covered duration")
    lo = _pos(e - max(s, u))
    hi = _pos(e - max(s, l))
    return DurationBounds(lo, hi)


def guarded(bounds: DurationBounds, guard_each_end: float) -> DurationBounds:
    """Conservative symmetric clock-guard transform.

    Trimming g from each end of an overlap can remove at most 2g duration.
    """
    if guard_each_end < 0:
        raise ValueError("guard must be nonnegative")
    shrink = 2.0 * guard_each_end
    return DurationBounds(_pos(bounds.lower - shrink), _pos(bounds.upper - shrink))


def prevalence_bounds(bounds: Iterable[DurationBounds]) -> Tuple[float, float]:
    """Sharp event-fraction bounds absent cross-event restrictions."""
    items = list(bounds)
    if not items:
        raise ValueError("at least one event is required")
    n = len(items)
    lo = sum(b.lower > 0 for b in items) / n
    hi = sum(b.upper > 0 for b in items) / n
    return lo, hi


def total_duration_bounds(bounds: Iterable[DurationBounds]) -> DurationBounds:
    """Sharp total-duration bounds absent cross-event restrictions."""
    items = list(bounds)
    if not items:
        raise ValueError("at least one event is required")
    return DurationBounds(sum(b.lower for b in items), sum(b.upper for b in items))


def width_bound_holds(bounds: DurationBounds, transition_bracket_width: float, episode_width: float) -> bool:
    """Check the analytic width inequality w(D) <= min(w(A), w(BGP))."""
    if transition_bracket_width < 0 or episode_width < 0:
        raise ValueError("widths must be nonnegative")
    return bounds.width <= min(transition_bracket_width, episode_width) + 1e-12


def exceedance_fraction_bounds(bounds: Iterable[DurationBounds], threshold: float = 0.0) -> Tuple[float, float]:
    """Sharp bounds for Pr(D > threshold) over a finite event collection.

    The result is pointwise sharp in the threshold when event-level latent
    timings are otherwise unrestricted across events.
    """
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    items = list(bounds)
    if not items:
        raise ValueError("at least one event is required")
    n = len(items)
    lo = sum(b.lower > threshold for b in items) / n
    hi = sum(b.upper > threshold for b in items) / n
    return lo, hi


def quorum_count_bounds(bounds: Iterable[DurationBounds], threshold: float = 0.0) -> Tuple[int, int]:
    """Sharp source-count bounds for the number of local gaps exceeding a threshold."""
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    items = list(bounds)
    if not items:
        raise ValueError("at least one source pair is required")
    lo = sum(b.lower > threshold for b in items)
    hi = sum(b.upper > threshold for b in items)
    return lo, hi


def quorum_classification(bounds: Iterable[DurationBounds], k: int, threshold: float = 0.0) -> str:
    """Classify a k-of-M confirmation rule without point-imputing local timings.

    Returns ``quorum_confirmed`` when every feasible latent timing assignment
    has at least k local gaps above ``threshold``; ``quorum_ruled_out`` when
    no feasible assignment can reach k; otherwise ``quorum_ambiguous``.
    """
    items = list(bounds)
    if not items:
        raise ValueError("at least one source pair is required")
    if not 1 <= k <= len(items):
        raise ValueError("k must lie between 1 and the number of source pairs")
    lo, hi = quorum_count_bounds(items, threshold)
    if lo >= k:
        return "quorum_confirmed"
    if hi < k:
        return "quorum_ruled_out"
    return "quorum_ambiguous"


def point_observation_classification(direction: str, l: float, u: float, p: float) -> str:
    """Identify a binary gap from one covered BGP edge observation at time p.

    Addition truth is p < A; removal truth is p >= A for latent A in [l,u].
    The return values preserve ambiguity instead of imputing A.
    """
    if l > u:
        raise ValueError("transition lower bound exceeds upper bound")
    if direction == "addition":
        if p < l:
            return "definite_gap"
        if p >= u:
            return "no_gap"
        return "timing_ambiguous"
    if direction == "removal":
        if p >= u:
            return "definite_gap"
        if p < l:
            return "no_gap"
        return "timing_ambiguous"
    raise ValueError("direction must be 'addition' or 'removal'")

@dataclass(frozen=True)
class CoupledQuorumResult:
    theta_lower: float
    theta_upper: float
    count_lower: int
    count_upper: int
    classification: str

    def __post_init__(self) -> None:
        if self.theta_lower > self.theta_upper:
            raise ValueError("infeasible shared transition interval")
        if self.count_lower < 0 or self.count_upper < self.count_lower:
            raise ValueError("invalid coupled quorum bounds")


def shared_transition_interval(
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
) -> Tuple[float, float]:
    """Exact feasible interval for a shared latent event time theta.

    Source j obeys A_j = theta + delta_j with A_j in [L_j,U_j] and
    delta_j in [alpha_j,beta_j]. Conditional on theta, delay choices are
    otherwise unrestricted across sources. Raises ValueError when the model
    is infeasible.
    """
    bs=list(brackets); ds=list(delay_envelopes)
    if not bs or len(bs)!=len(ds):
        raise ValueError("brackets and delay envelopes must be nonempty and aligned")
    lowers=[]; uppers=[]
    for (l,u),(a,b) in zip(bs,ds):
        if l>u: raise ValueError("invalid transition bracket")
        if a>b: raise ValueError("invalid delay envelope")
        lowers.append(l-b)
        uppers.append(u-a)
    tl=max(lowers); tu=min(uppers)
    if tl>tu:
        raise ValueError("shared-event model infeasible")
    return tl,tu


def shared_transition_tension(
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
) -> float:
    """Nonnegative separation of incompatible shared-transition constraints."""
    bs=list(brackets); ds=list(delay_envelopes)
    if not bs or len(bs)!=len(ds):
        raise ValueError("brackets and delay envelopes must be nonempty and aligned")
    left=[]; right=[]
    for (l,u),(a,b) in zip(bs,ds):
        if l>u or a>b: raise ValueError("invalid interval")
        left.append(l-b); right.append(u-a)
    return _pos(max(left)-min(right))


def uniform_feasibility_slack(
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
) -> float:
    """Minimal symmetric theta-interval slack needed to restore feasibility.

    If every source-implied feasible theta interval is expanded by epsilon on
    both sides, the smallest epsilon yielding a nonempty intersection is
    Delta/2, where Delta is ``shared_transition_tension``.
    """
    return shared_transition_tension(brackets, delay_envelopes) / 2.0


def point_resolution_margin(l: float, u: float, p: float) -> float:
    """Infimal one-sided bracket tightening required to resolve an ambiguous point probe.

    For p strictly inside [l,u], moving either supported endpoint past p resolves
    the binary threshold decision.  The infimum of the required endpoint motion
    is min(p-l, u-p). Returns 0 outside the ambiguous region.
    """
    if l>u:
        raise ValueError("transition lower bound exceeds upper bound")
    if not l < p < u:
        return 0.0
    return min(p-l,u-p)


def conditional_transition_interval(
    l: float, u: float, alpha: float, beta: float, theta: float
) -> Tuple[float, float]:
    """Exact feasible source-local transition interval conditional on theta."""
    if l>u or alpha>beta: raise ValueError("invalid interval")
    lo=max(l,theta+alpha); hi=min(u,theta+beta)
    if lo>hi+1e-12:
        raise ValueError("theta is incompatible with this source")
    if lo>hi:  # numerical contact at a closed-interval boundary
        m=(lo+hi)/2.0; lo=hi=m
    return lo,hi


def _conditional_duration_bounds(
    direction: str, l: float, u: float, alpha: float, beta: float,
    theta: float, s: float, e: float
) -> DurationBounds:
    lo,hi=conditional_transition_interval(l,u,alpha,beta,theta)
    if direction=="addition": return addition_bounds(lo,hi,s,e)
    if direction=="removal": return removal_bounds(lo,hi,s,e)
    raise ValueError("direction must be 'addition' or 'removal'")


def coupled_quorum_classification(
    direction: str,
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    bgp_episodes: Iterable[Tuple[float, float]],
    k: int,
    threshold: float = 0.0,
) -> CoupledQuorumResult:
    """Sharp k-of-M quorum bounds under a shared latent event and bounded delays.

    The support assumption is factorized conditional on theta: after imposing
    A_j=theta+delta_j and each source's bracket/delay envelope, no further
    cross-source restriction is assumed. For a common addition event the
    forced-positive count is minimized at theta_lower and possible-positive
    count maximized at theta_upper; removal reverses those endpoints.
    """
    if threshold<0: raise ValueError("threshold must be nonnegative")
    bs=list(brackets); ds=list(delay_envelopes); eps=list(bgp_episodes)
    if not bs or len(bs)!=len(ds) or len(bs)!=len(eps):
        raise ValueError("all source lists must be nonempty and aligned")
    if not 1<=k<=len(bs): raise ValueError("invalid quorum k")
    tl,tu=shared_transition_interval(bs,ds)
    low_theta, high_theta=(tl,tu) if direction=="addition" else (tu,tl)
    forced=0; possible=0
    for (l,u),(a,b),(s,e) in zip(bs,ds,eps):
        blo=_conditional_duration_bounds(direction,l,u,a,b,low_theta,s,e)
        bhi=_conditional_duration_bounds(direction,l,u,a,b,high_theta,s,e)
        # For additions, low_theta gives the smallest conditional duration and
        # high_theta the largest. Removal endpoint order was reversed above.
        forced += blo.lower > threshold
        possible += bhi.upper > threshold
    if forced>=k: label="quorum_confirmed"
    elif possible<k: label="quorum_ruled_out"
    else: label="quorum_ambiguous"
    return CoupledQuorumResult(tl,tu,forced,possible,label)

@dataclass(frozen=True)
class RobustCoupledQuorumResult:
    """Sharp interval hull of attainable quorum counts under up to q invalid coupling constraints."""
    count_lower: int
    count_upper: int
    classification: str
    q: int
    feasible_theta_candidates: int

    def __post_init__(self) -> None:
        if self.count_lower < 0 or self.count_upper < self.count_lower:
            raise ValueError("invalid robust coupled quorum bounds")
        if self.q < 0:
            raise ValueError("q must be nonnegative")
        if self.feasible_theta_candidates < 0:
            raise ValueError("invalid candidate count")


def _source_theta_interval(
    bracket: Tuple[float, float], delay: Tuple[float, float]
) -> Tuple[float, float]:
    l,u=bracket; a,b=delay
    if l>u or a>b:
        raise ValueError("invalid interval")
    return l-b, u-a


def q_relaxed_transition_components(
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    q: int,
) -> list[Tuple[float, float]]:
    """Exact 1-D q-relaxed support for a common latent transition.

    The returned closed components contain theta values compatible with at
    least M-q source-to-common-event constraints.  This is standard relaxed
    interval intersection; it is exposed here as a support primitive rather
    than claimed as a novel contribution.
    """
    bs=list(brackets); ds=list(delay_envelopes)
    if not bs or len(bs)!=len(ds):
        raise ValueError("brackets and delay envelopes must be nonempty and aligned")
    m=len(bs)
    if not 0<=q<=m:
        raise ValueError("q must lie between 0 and the number of sources")
    if q==m:
        return [(-float('inf'), float('inf'))]
    hs=[_source_theta_interval(b,d) for b,d in zip(bs,ds)]
    pts=sorted({x for h in hs for x in h})

    def ok(x: float) -> bool:
        return sum(lo-1e-12<=x<=hi+1e-12 for lo,hi in hs) >= m-q

    atoms=[]
    for i,x in enumerate(pts):
        if ok(x):
            atoms.append((x,x))
        if i+1<len(pts):
            y=pts[i+1]
            if y>x:
                mid=(x+y)/2.0
                if ok(mid):
                    atoms.append((x,y))
    if not atoms:
        return []
    atoms.sort()
    out=[]
    for lo,hi in atoms:
        if not out or lo>out[-1][1]+1e-12:
            out.append([lo,hi])
        else:
            out[-1][1]=max(out[-1][1],hi)
    return [(float(lo),float(hi)) for lo,hi in out]


def minimum_relaxation_budget(
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
) -> int:
    """Smallest q for which the q-relaxed common-transition support is nonempty."""
    bs=list(brackets); ds=list(delay_envelopes)
    if not bs or len(bs)!=len(ds):
        raise ValueError("brackets and delay envelopes must be nonempty and aligned")
    for q in range(len(bs)+1):
        if q_relaxed_transition_components(bs,ds,q):
            return q
    raise AssertionError("q=M must always be feasible")


def _robust_candidate_thetas(
    direction: str,
    brackets: list[Tuple[float, float]],
    delay_envelopes: list[Tuple[float, float]],
    bgp_episodes: list[Tuple[float, float]],
    threshold: float,
) -> list[float]:
    """Finite exact theta test set for robust threshold-count extrema.

    Each source contributes two q-relaxed-support endpoints and at most two
    threshold switch points.  Evaluating every unique breakpoint and one
    midpoint of every adjacent open cell is exact, hence at most 8M-1
    points before duplicate removal.
    """
    if direction not in {"addition","removal"}:
        raise ValueError("direction must be 'addition' or 'removal'")
    pts=[]
    for (l,u),(alpha,beta),(s,e) in zip(brackets,delay_envelopes,bgp_episodes):
        if l>u or alpha>beta or s>=e:
            raise ValueError("invalid source geometry")
        hl,hu=l-beta,u-alpha
        pts.extend((hl,hu))
        if threshold < e-s:
            boundary=(s+threshold) if direction=="addition" else (e-threshold)
            # Conditional forced/possible threshold indicators can only
            # change when theta crosses boundary-alpha or boundary-beta.
            pts.extend((boundary-alpha,boundary-beta))
    uniq=sorted(set(float(x) for x in pts))
    if not uniq:
        return []
    cand=list(uniq)
    cand.extend((x+y)/2.0 for x,y in zip(uniq,uniq[1:]) if y>x)
    return sorted(set(cand))


def robust_coupled_quorum_classification(
    direction: str,
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    bgp_episodes: Iterable[Tuple[float, float]],
    k: int,
    q: int,
    threshold: float = 0.0,
) -> RobustCoupledQuorumResult:
    """Sharp k-of-M quorum bounds with up to q invalid coupling constraints.

    Every source-local transition bracket remains valid.  For at least M-q
    sources there exists a common theta satisfying A_j=theta+delta_j with
    delta_j in that source's stated delay envelope.  Up to q source-to-common
    coupling constraints may be invalid; those sources retain only their
    source-local interval evidence instead of being deleted from the quorum.

    The identity of relaxed constraints is unknown and is optimized as a
    nuisance variable.  ``count_lower`` and ``count_upper`` are the sharp
    extrema (the interval hull) of the attainable integer count set; that set
    itself need not be contiguous.  The extrema are sufficient for every
    monotone k-of-M decision.  This is not an outlier-classification procedure.
    """
    if threshold<0:
        raise ValueError("threshold must be nonnegative")
    bs=list(brackets); ds=list(delay_envelopes); eps=list(bgp_episodes)
    if not bs or len(bs)!=len(ds) or len(bs)!=len(eps):
        raise ValueError("all source lists must be nonempty and aligned")
    m=len(bs)
    if not 1<=k<=m:
        raise ValueError("invalid quorum k")
    if not 0<=q<=m:
        raise ValueError("q must lie between 0 and M")

    local=[]
    for (l,u),(s,e) in zip(bs,eps):
        if direction=="addition":
            local.append(addition_bounds(l,u,s,e))
        elif direction=="removal":
            local.append(removal_bounds(l,u,s,e))
        else:
            raise ValueError("direction must be 'addition' or 'removal'")

    # q=M means no shared-event constraint is assumed, exactly recovering
    # the separable count set.
    if q==m:
        lo,hi=quorum_count_bounds(local,threshold)
        label=("quorum_confirmed" if lo>=k else
               "quorum_ruled_out" if hi<k else "quorum_ambiguous")
        return RobustCoupledQuorumResult(lo,hi,label,q,0)

    hs=[_source_theta_interval(b,d) for b,d in zip(bs,ds)]
    candidates=_robust_candidate_thetas(direction,bs,ds,eps,threshold)
    global_lo=None; global_hi=None; feasible_n=0
    for theta in candidates:
        compatible=[lo-1e-12<=theta<=hi+1e-12 for lo,hi in hs]
        mandatory_outliers=m-sum(compatible)
        if mandatory_outliers>q:
            continue
        feasible_n+=1
        extra=q-mandatory_outliers

        base_forced=0; reductions=[]
        base_possible=0; gains=[]
        for is_inlier,(l,u),(a,b),(s,e),lb in zip(compatible,bs,ds,eps,local):
            lf=int(lb.lower>threshold); lp=int(lb.upper>threshold)
            if not is_inlier:
                base_forced+=lf; base_possible+=lp
                continue
            cb=_conditional_duration_bounds(direction,l,u,a,b,theta,s,e)
            cf=int(cb.lower>threshold); cp=int(cb.upper>threshold)
            base_forced+=cf; base_possible+=cp
            # Relaxing a valid coupling constraint can only return to the
            # wider local set, so reductions/gains are nonnegative.
            reductions.append(cf-lf)
            gains.append(lp-cp)

        # The unweighted relaxation effects are binary: each compatible
        # source can change the forced or possible count by at most one.
        # Hence sorting is unnecessary; the best use of the remaining
        # relaxation budget is determined by the number of unit effects.
        lower_leverage=sum(reductions)
        upper_leverage=sum(gains)
        theta_lo=base_forced-min(extra,lower_leverage)
        theta_hi=base_possible+min(extra,upper_leverage)
        global_lo=theta_lo if global_lo is None else min(global_lo,theta_lo)
        global_hi=theta_hi if global_hi is None else max(global_hi,theta_hi)

    if global_lo is None or global_hi is None:
        raise ValueError("q-relaxed shared-event model infeasible")
    label=("quorum_confirmed" if global_lo>=k else
           "quorum_ruled_out" if global_hi<k else "quorum_ambiguous")
    return RobustCoupledQuorumResult(int(global_lo),int(global_hi),label,q,feasible_n)


@dataclass(frozen=True)
class RobustCoupledScoreResult:
    """Sharp interval hull for a nonnegative weighted downstream score."""
    score_lower: float
    score_upper: float
    q: int
    feasible_theta_candidates: int

    def __post_init__(self) -> None:
        if self.score_lower < -1e-12 or self.score_upper + 1e-12 < self.score_lower:
            raise ValueError("invalid robust coupled score bounds")
        if self.q < 0:
            raise ValueError("q must be nonnegative")


def robust_coupled_weighted_score_bounds(
    direction: str,
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    bgp_episodes: Iterable[Tuple[float, float]],
    weights: Iterable[float],
    q: int,
    threshold: float = 0.0,
) -> RobustCoupledScoreResult:
    """Sharp extrema of sum_j w_j 1{D_j>threshold} under A6(q).

    Weights must be nonnegative.  Relaxed sources retain their source-local
    evidence.  At a fixed theta, relaxing a compatible source can decrease
    the forced score by w_j(f_j-l_j) or increase the possible score by
    w_j(u_j-p_j).  Selecting the largest available effects is exact.
    """
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    bs=list(brackets); ds=list(delay_envelopes); eps=list(bgp_episodes); ws=list(weights)
    if not bs or len(bs)!=len(ds) or len(bs)!=len(eps) or len(bs)!=len(ws):
        raise ValueError("all source lists must be nonempty and aligned")
    if any(w < 0 for w in ws):
        raise ValueError("weights must be nonnegative")
    m=len(bs)
    if not 0<=q<=m:
        raise ValueError("q must lie between 0 and M")
    if direction not in {"addition","removal"}:
        raise ValueError("direction must be 'addition' or 'removal'")

    local=[]
    for (l,u),(s,e) in zip(bs,eps):
        local.append(addition_bounds(l,u,s,e) if direction=="addition"
                     else removal_bounds(l,u,s,e))

    if q==m:
        lo=sum(w*int(lb.lower>threshold) for w,lb in zip(ws,local))
        hi=sum(w*int(lb.upper>threshold) for w,lb in zip(ws,local))
        return RobustCoupledScoreResult(float(lo),float(hi),q,0)

    hs=[_source_theta_interval(b,d) for b,d in zip(bs,ds)]
    candidates=_robust_candidate_thetas(direction,bs,ds,eps,threshold)
    global_lo=None; global_hi=None; feasible_n=0
    for theta in candidates:
        compatible=[lo-1e-12<=theta<=hi+1e-12 for lo,hi in hs]
        mandatory_outliers=m-sum(compatible)
        if mandatory_outliers>q:
            continue
        feasible_n+=1
        extra=q-mandatory_outliers
        base_forced=0.0; reductions=[]
        base_possible=0.0; gains=[]
        for is_inlier,(l,u),(a,b),(s,e),lb,w in zip(compatible,bs,ds,eps,local,ws):
            lf=int(lb.lower>threshold); lp=int(lb.upper>threshold)
            if not is_inlier:
                base_forced+=w*lf; base_possible+=w*lp
                continue
            cb=_conditional_duration_bounds(direction,l,u,a,b,theta,s,e)
            cf=int(cb.lower>threshold); cp=int(cb.upper>threshold)
            base_forced+=w*cf; base_possible+=w*cp
            reductions.append(w*(cf-lf))
            gains.append(w*(lp-cp))
        reductions.sort(reverse=True); gains.sort(reverse=True)
        theta_lo=base_forced-sum(reductions[:extra])
        theta_hi=base_possible+sum(gains[:extra])
        global_lo=theta_lo if global_lo is None else min(global_lo,theta_lo)
        global_hi=theta_hi if global_hi is None else max(global_hi,theta_hi)
    if global_lo is None or global_hi is None:
        raise ValueError("q-relaxed shared-event model infeasible")
    return RobustCoupledScoreResult(float(global_lo),float(global_hi),q,feasible_n)

def robust_coupled_quorum_count_set(
    direction: str,
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    bgp_episodes: Iterable[Tuple[float, float]],
    q: int,
    threshold: float = 0.0,
) -> tuple[int, ...]:
    """Exact attainable positive-source count set under A6(q).

    Unlike the interval hull returned by ``robust_coupled_quorum_classification``,
    this function preserves possible holes in the integer identified set.  For
    each exact theta cell representative, a dynamic program tracks relaxation
    budget and all attainable 0/1 source contributions.  The finite theta test
    set is the same breakpoint-plus-midpoint set used for the sharp extrema.
    """
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    bs=list(brackets); ds=list(delay_envelopes); eps=list(bgp_episodes)
    if not bs or len(bs)!=len(ds) or len(bs)!=len(eps):
        raise ValueError("all source lists must be nonempty and aligned")
    m=len(bs)
    if not 0<=q<=m:
        raise ValueError("q must lie between 0 and M")
    if direction not in {"addition","removal"}:
        raise ValueError("direction must be 'addition' or 'removal'")

    local=[]
    for (l,u),(s,e) in zip(bs,eps):
        local.append(addition_bounds(l,u,s,e) if direction=="addition"
                     else removal_bounds(l,u,s,e))

    def vals(lo: int, hi: int) -> tuple[int, ...]:
        return (lo,) if lo==hi else (0,1)

    if q==m:
        lo,hi=quorum_count_bounds(local,threshold)
        return tuple(range(lo,hi+1))

    hs=[_source_theta_interval(b,d) for b,d in zip(bs,ds)]
    candidates=_robust_candidate_thetas(direction,bs,ds,eps,threshold)
    attainable=set()
    for theta in candidates:
        compatible=[lo-1e-12<=theta<=hi+1e-12 for lo,hi in hs]
        if m-sum(compatible)>q:
            continue
        # DP state: (number of relaxed constraints used, positive count).
        states={(0,0)}
        for is_inlier,(l,u),(a,b),(s,e),lb in zip(compatible,bs,ds,eps,local):
            lf=int(lb.lower>threshold); lp=int(lb.upper>threshold)
            nxt=set()
            if is_inlier:
                cb=_conditional_duration_bounds(direction,l,u,a,b,theta,s,e)
                cf=int(cb.lower>threshold); cp=int(cb.upper>threshold)
                coupled_vals=vals(cf,cp)
                local_vals=vals(lf,lp)
                for used,count in states:
                    for z in coupled_vals:
                        nxt.add((used,count+z))
                    if used<q:
                        for z in local_vals:
                            nxt.add((used+1,count+z))
            else:
                # Incompatibility forces this coupling constraint to be relaxed.
                local_vals=vals(lf,lp)
                for used,count in states:
                    if used<q:
                        for z in local_vals:
                            nxt.add((used+1,count+z))
            states=nxt
            if not states:
                break
        attainable.update(count for used,count in states if used<=q)
    if not attainable:
        raise ValueError("q-relaxed shared-event model infeasible")
    return tuple(sorted(attainable))



@dataclass(frozen=True)
class QuorumRelaxationCertificate:
    """Decision-stability certificate as the relaxation budget q increases."""
    classification: str
    baseline_q: int
    maximum_preserving_q: int
    first_ambiguous_q: int | None

    def __post_init__(self) -> None:
        if self.classification not in {"quorum_confirmed", "quorum_ruled_out"}:
            raise ValueError("certificate requires a resolved baseline decision")
        if self.baseline_q < 0 or self.maximum_preserving_q < self.baseline_q:
            raise ValueError("invalid relaxation certificate")
        if self.first_ambiguous_q is not None and self.first_ambiguous_q != self.maximum_preserving_q + 1:
            raise ValueError("first ambiguous q must immediately follow the preserving budget")

    @property
    def additional_relaxations_tolerated(self) -> int:
        return self.maximum_preserving_q - self.baseline_q


def quorum_relaxation_certificate(
    direction: str,
    brackets: Iterable[Tuple[float, float]],
    delay_envelopes: Iterable[Tuple[float, float]],
    bgp_episodes: Iterable[Tuple[float, float]],
    k: int,
    baseline_q: int = 0,
    threshold: float = 0.0,
) -> QuorumRelaxationCertificate:
    """Largest relaxation budget preserving a resolved k-of-M decision.

    Because the A6(q) feasible assignment family is nested in q, a resolved
    decision can only persist or become ambiguous as q grows; it cannot flip
    directly to the opposite resolved decision.  This function returns the
    largest q >= ``baseline_q`` that preserves the baseline resolved label.
    """
    bs=list(brackets); ds=list(delay_envelopes); eps=list(bgp_episodes)
    if not bs or len(bs)!=len(ds) or len(bs)!=len(eps):
        raise ValueError("all source lists must be nonempty and aligned")
    m=len(bs)
    if not 0<=baseline_q<=m:
        raise ValueError("baseline_q must lie between 0 and M")
    base=robust_coupled_quorum_classification(
        direction,bs,ds,eps,k,baseline_q,threshold).classification
    if base=="quorum_ambiguous":
        raise ValueError("baseline decision must be resolved")
    qmax=baseline_q
    first_ambiguous=None
    opposite=("quorum_ruled_out" if base=="quorum_confirmed" else "quorum_confirmed")
    for q in range(baseline_q+1,m+1):
        cur=robust_coupled_quorum_classification(
            direction,bs,ds,eps,k,q,threshold).classification
        if cur==opposite:
            raise AssertionError("nested identified sets cannot reverse a resolved quorum label")
        if cur=="quorum_ambiguous":
            first_ambiguous=q
            break
        qmax=q
    return QuorumRelaxationCertificate(base,baseline_q,qmax,first_ambiguous)


def conformal_q_budget(violation_counts: Iterable[int], alpha: float, m_sources: int) -> int:
    """Held-out finite-sample upper prediction bound for a future violation count.

    Let V_i count source-to-common-event constraints violated by trusted
    calibration event i. Under exchangeability of calibration counts and the
    next event's count, q_hat returned here satisfies marginal
    P(V_next <= q_hat) >= 1-alpha.  The rule calibrates a sensitivity budget;
    it does not use or optimize any downstream quorum label.
    """
    import math
    vals=[int(v) for v in violation_counts]
    if not vals:
        raise ValueError("at least one calibration event is required")
    if not (0 < alpha < 1):
        raise ValueError("alpha must lie in (0,1)")
    if m_sources < 1:
        raise ValueError("m_sources must be positive")
    if any(v < 0 or v > m_sources for v in vals):
        raise ValueError("violation counts must lie in [0,M]")
    n=len(vals)
    k=int(math.ceil((n+1)*(1-alpha)))
    if k>n:
        return int(m_sources)
    return int(sorted(vals)[k-1])
