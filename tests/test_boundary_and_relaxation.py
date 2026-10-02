"""Boundary-semantics and relaxation-certificate regression tests.

These tests lock the mathematical convention used in the manuscript:
RPKI transition brackets are closed [L,U], BGP episodes are [S,E), and
threshold decisions use the strict event D > tau.
"""
from interval_identification import (
    DurationBounds,
    addition_bounds,
    removal_bounds,
    quorum_count_bounds,
    conditional_transition_interval,
    robust_coupled_quorum_classification,
    robust_coupled_quorum_count_set,
    robust_coupled_weighted_score_bounds,
    quorum_relaxation_certificate,
)
from exact_oracle_validation import oracle as count_oracle
from weighted_oracle_validation import oracle as weighted_oracle


def test_closed_addition_upper_endpoint_is_attainable():
    # A in [0,2], BGP episode [0,1): A=1 or A=2 attains one full unit.
    assert addition_bounds(0.0, 2.0, 0.0, 1.0) == DurationBounds(0.0, 1.0)


def test_closed_removal_upper_transition_endpoint_attains_lower_bound():
    # A=U=2 is feasible, so the lower duration 10-2=8 is attained.
    assert removal_bounds(0.0, 2.0, 0.0, 10.0) == DurationBounds(8.0, 10.0)


def test_bgp_exclusive_end_is_compatible_with_elapsed_duration_formula():
    # Transition exactly at exclusive E means addition mismatch spans [S,E)
    # while removal mismatch has zero duration.
    assert addition_bounds(10.0, 10.0, 0.0, 10.0) == DurationBounds(10.0, 10.0)
    assert removal_bounds(10.0, 10.0, 0.0, 10.0) == DurationBounds(0.0, 0.0)


def test_strict_threshold_equality_is_not_positive():
    # The estimand is 1{D > tau}, not 1{D >= tau}.
    assert quorum_count_bounds([DurationBounds(1.0, 1.0)], 1.0) == (0, 0)
    assert quorum_count_bounds([DurationBounds(1.0, 2.0)], 1.0) == (0, 1)


def test_conditional_intersection_retains_closed_point_contacts():
    # H=[1,7].  At each endpoint the conditional A-set is a singleton.
    assert conditional_transition_interval(4.0, 8.0, 1.0, 3.0, 1.0) == (4.0, 4.0)
    assert conditional_transition_interval(4.0, 8.0, 1.0, 3.0, 7.0) == (8.0, 8.0)


def test_exact_count_set_matches_independent_oracle_at_all_q_on_boundary_case():
    # Several H endpoints and threshold switch points coincide exactly.
    direction='addition'
    bs=[(0.0,1.0),(0.5,1.5),(1.0,2.0)]
    ds=[(0.0,0.5),(0.0,0.5),(0.0,0.5)]
    eps=[(0.5,2.0),(1.0,2.5),(1.5,3.0)]
    tau=0.5
    for q in range(4):
        expected=count_oracle(direction,bs,ds,eps,q,tau)
        try:
            got=robust_coupled_quorum_count_set(direction,bs,ds,eps,q,tau)
        except ValueError:
            got=tuple()
        assert got==expected


def test_weighted_zero_weights_and_full_q_range_match_independent_oracle():
    direction='removal'
    bs=[(0.0,1.0),(0.5,1.5),(1.0,2.0)]
    ds=[(0.0,0.5),(0.0,0.5),(0.0,0.5)]
    eps=[(-0.5,1.0),(0.0,1.5),(0.5,2.0)]
    weights=[0.0,2.0,5.0]
    tau=0.5
    for q in range(4):
        try:
            expected=weighted_oracle(direction,bs,ds,eps,weights,q,tau)
        except ValueError:
            expected=None
        try:
            got=robust_coupled_weighted_score_bounds(direction,bs,ds,eps,weights,q,tau)
            observed=(got.score_lower,got.score_upper)
        except ValueError:
            observed=None
        assert observed==expected


def test_relaxation_certificate_matches_nested_decision_loss():
    # Strict coupling forces all three additions positive.  Allowing one
    # coupling failure expands the assignment family enough to lose, but not
    # reverse, the 3-of-3 conclusion.
    bs=[(1.0,2.0),(0.0,2.0),(0.0,2.0)]
    ds=[(0.0,0.0)]*3
    eps=[(0.5,3.0)]*3
    q0=robust_coupled_quorum_classification('addition',bs,ds,eps,3,0,0.0)
    q1=robust_coupled_quorum_classification('addition',bs,ds,eps,3,1,0.0)
    assert q0.classification=='quorum_confirmed'
    assert q1.classification=='quorum_ambiguous'
    cert=quorum_relaxation_certificate('addition',bs,ds,eps,3,0,0.0)
    assert cert.classification=='quorum_confirmed'
    assert cert.maximum_preserving_q==0
    assert cert.first_ambiguous_q==1
    assert cert.additional_relaxations_tolerated==0


def test_closed_hull_is_fail_closed_for_excluded_endpoint_equalities():
    # If raw endpoint semantics exclude an endpoint, the closed support can be
    # more conservative at a strict-threshold equality, but cannot create an
    # incorrect resolved conclusion. Addition over J=(0,2] has D>0 always,
    # while its closed hull [0,2] is ambiguous at tau=0 because A=0 is added.
    b = addition_bounds(0.0, 2.0, 0.0, 3.0)
    assert b == DurationBounds(0.0, 2.0)
    assert quorum_count_bounds([b], 0.0) == (0, 1)

    # Removal over J=[0,2) has D>8 always for episode [0,10), while the
    # closed hull includes A=2 and therefore remains conservatively ambiguous.
    b = removal_bounds(0.0, 2.0, 0.0, 10.0)
    assert b == DurationBounds(8.0, 10.0)
    assert quorum_count_bounds([b], 8.0) == (0, 1)


def test_resolved_closed_hull_decisions_are_sound_for_endpoint_subsets():
    # A closed-hull positive conclusion remains positive for any subset of the
    # same support; likewise for a ruled-out conclusion. These concrete cases
    # guard the endpoint-closure lemma used in the manuscript.
    positive = addition_bounds(1.0, 2.0, 0.0, 3.0)
    assert quorum_count_bounds([positive], 0.5) == (1, 1)
    for a in (1.0, 1.25, 1.999999, 2.0):
        d = max(min(3.0, a) - 0.0, 0.0)
        assert d > 0.5

    ruled_out = addition_bounds(0.0, 1.0, 2.0, 3.0)
    assert quorum_count_bounds([ruled_out], 0.0) == (0, 0)
    for a in (0.0, 0.25, 0.999999, 1.0):
        d = max(min(3.0, a) - 2.0, 0.0)
        assert not (d > 0.0)
