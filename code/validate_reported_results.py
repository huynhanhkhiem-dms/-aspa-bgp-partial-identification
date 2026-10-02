#!/usr/bin/env python3
"""Fail-closed checks for every numeric claim reported in the manuscript tables/text."""
from __future__ import annotations
import csv, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'data'/'input'
OUT=ROOT/'data'/'output'
POS={"route_observed_before_embedded_signing_time","route_observed_after_embedded_signing_time"}


def _j(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def _close(a,b,tol=5e-4):
    if not math.isclose(float(a),float(b),abs_tol=tol,rel_tol=0):
        raise AssertionError(f"expected {b}, got {a}")


def main():
    # Synthetic local table: pooled values used in Table II.
    local=_j('synthetic_identification_stress.summary.json')
    expected_local={
        0.01:(0.93,0.24),
        0.05:(4.61,1.15),
        0.10:(9.37,2.32),
        0.25:(23.99,6.07),
        0.50:(48.81,12.33),
    }
    assert local['all_resolved_decisions_correct'] is True
    assert sum(r['n_total'] for r in local['pooled_by_width'])==2_000_000
    for r in local['pooled_by_width']:
        w=round(float(r['bracket_width']),2)
        amb,err=expected_local[w]
        _close(round(r['ambiguous_pct_mean'],2),amb,1e-9)
        _close(round(r['midpoint_error_pct_mean'],2),err,1e-9)
        assert r['resolved_errors_total']==0

    # Synthetic quorum table: 500k events, 8 source pairs, k=5.
    quorum=_j('synthetic_quorum_stress.summary.json')
    expected_quorum={
        0.01:(1.91,0.52),
        0.05:(9.71,2.39),
        0.10:(19.46,4.61),
        0.25:(47.12,10.32),
        0.50:(80.95,17.13),
    }
    assert quorum['all_resolved_quorum_decisions_correct'] is True
    assert quorum['sources_per_event']==8 and quorum['quorum_k']==5
    assert sum(r['n_events'] for r in quorum['rows'])==500_000
    for r in quorum['rows']:
        w=round(float(r['bracket_width']),2)
        amb,err=expected_quorum[w]
        _close(round(r['ambiguous_pct'],2),amb,1e-9)
        _close(round(r['midpoint_quorum_error_pct'],2),err,1e-9)
        assert r['resolved_errors']==0


    # Coupled shared-event quorum stress test: exact numbers reported in manuscript Table II.
    coupled=_j('synthetic_coupled_quorum_stress.summary.json')
    expected_coupled={
        0.02:(6.120,3.155,2.965,1.620),
        0.05:(15.645,7.880,7.765,3.615),
        0.10:(30.645,15.970,14.675,6.905),
        0.20:(57.350,30.585,26.765,12.345),
        0.35:(85.790,50.830,34.960,19.195),
    }
    assert coupled['all_coupled_resolved_decisions_correct'] is True
    assert coupled['no_separable_resolved_label_reversal'] is True
    assert coupled['all_generated_shared_models_feasible'] is True
    assert coupled['sources_per_event']==8 and coupled['quorum_k']==5
    assert sum(r['n_events'] for r in coupled['rows'])==100_000
    for r in coupled['rows']:
        w=round(float(r['bracket_width']),2)
        sep,cp,gain,mid=expected_coupled[w]
        _close(round(r['separable_ambiguous_pct'],3),sep,1e-9)
        _close(round(r['coupled_ambiguous_pct'],3),cp,1e-9)
        _close(round(r['ambiguity_reduction_pp'],3),gain,1e-9)
        _close(round(r['midpoint_quorum_error_pct'],3),mid,1e-9)
        assert r['coupled_resolved_errors']==0
        assert r['separable_resolved_label_reversals']==0
        assert r['shared_model_infeasible_events']==0

    # Multi-configuration strict-coupling generalization stress.
    general=_j('synthetic_coupled_quorum_generalization.summary.json')
    assert general['total_events']==90_000
    assert general['all_coupled_resolved_decisions_correct'] is True
    assert general['no_separable_resolved_label_reversal'] is True
    assert general['all_generated_shared_models_feasible'] is True
    assert len(general['rows'])==18
    _close(round(general['ambiguity_reduction_pp_min'],2),3.08,1e-9)
    _close(round(general['ambiguity_reduction_pp_max'],2),46.36,1e-9)
    assert {r['sources_per_event'] for r in general['rows']}=={4,6,8,12,16}
    assert all(r['coupled_resolved_errors']==0 for r in general['rows'])
    assert all(r['separable_resolved_label_reversals']==0 for r in general['rows'])
    assert all(r['shared_model_infeasible_events']==0 for r in general['rows'])

    # Robust q=1 coupling-misspecification stress: numbers reported in manuscript.
    robust=_j('synthetic_robust_coupling_stress.summary.json')
    expected_robust={
        0.00:(86.380,78.950,7.430,0.000,0.000,0.000),
        0.25:(86.350,77.570,8.780,2.810,0.550,1.076),
        0.50:(86.190,73.300,12.890,19.490,1.910,4.247),
        1.00:(86.360,64.620,21.740,69.480,1.870,9.149),
        2.00:(85.940,57.550,28.390,100.000,0.000,0.000),
    }
    assert robust['all_robust_resolved_decisions_correct'] is True
    assert robust['strict_model_can_be_feasible_and_wrong'] is True
    assert robust['sources_per_event']==8 and robust['quorum_k']==5 and robust['robust_q']==1
    assert sum(r['n_events'] for r in robust['rows'])==50_000
    for r in robust['rows']:
        sh=round(float(r['shift_in_bracket_widths']),2)
        sep,ra,gain,inf,wrong_all,wrong_res=expected_robust[sh]
        _close(round(r['separable_ambiguous_pct'],3),sep,1e-9)
        _close(round(r['robust_ambiguous_pct'],3),ra,1e-9)
        _close(round(r['robust_ambiguity_reduction_pp'],3),gain,1e-9)
        _close(round(r['strict_infeasible_pct'],3),inf,1e-9)
        _close(round(r['strict_wrong_resolved_pct_all_events'],3),wrong_all,1e-9)
        _close(round(r['strict_wrong_resolved_pct_of_resolved'],3),wrong_res,1e-9)
        assert r['robust_resolved_errors']==0
        assert r['max_feasible_theta_candidates_q1'] <= 8*8-1
        assert sum(r['minimum_relaxation_budget_counts'].values())==10_000
        assert sum(v for k,v in r['minimum_relaxation_budget_counts'].items() if int(k)>1)==0

    # Held-out conformal calibration of q: deterministic Monte Carlo numbers reported in text.
    qcal=_j('conformal_q_calibration.summary.json')
    assert qcal['m_sources']==8 and qcal['n_calibration_events']==199 and qcal['n_repetitions']==20_000
    _close(round(qcal['exchangeable']['coverage'],4),0.9714,1e-9)
    _close(round(qcal['deliberate_distribution_shift']['coverage'],5),0.71595,1e-9)
    assert qcal['checks']['exchangeable_empirical_coverage_at_least_nominal_minus_mc_tol'] is True
    assert qcal['checks']['shift_stress_is_lower_than_exchangeable'] is True

    # Shared-event model tension contamination stress.
    tension=_j('synthetic_coupling_tension_stress.summary.json')
    assert tension['clean_false_positive_pct']==0.0
    expected_tension={0.0:0.000,0.25:2.585,0.50:20.050,1.0:68.755,2.0:100.000}
    assert sum(r['n_events'] for r in tension['rows'])==100_000
    for r in tension['rows']:
        sh=float(r['shift_in_bracket_widths'])
        _close(round(r['infeasible_detected_pct'],3),expected_tension[sh],1e-9)
        _close(r['max_uniform_slack'],r['max_tension']/2.0,1e-12)

    # Cross-configuration robust generalization grid reported in Section 5.4/Table 5.
    grid=_j('robust_generalization_grid.summary.json')
    assert grid['geometry_cells']==81
    assert grid['generated_events']==81_000
    assert grid['quorum_decisions']==216_000
    assert grid['reported_settings']==216
    assert grid['positive_reduction_settings']==198
    assert grid['unchanged_settings']==18
    assert grid['all_robust_resolved_decisions_correct'] is True
    assert grid['robust_never_more_ambiguous_than_separable'] is True
    _close(round(grid['mean_ambiguity_reduction_pp'],2),14.65,1e-9)
    _close(round(grid['max_ambiguity_reduction_pp'],2),58.20,1e-9)
    expected_by_m={
        4:(27_000,54_000,6.08,24.50,0),
        8:(27_000,81_000,13.16,40.50,0),
        16:(27_000,81_000,21.84,58.20,0),
    }
    for r in grid['by_m']:
        exp=expected_by_m[r['m_sources']]
        assert (r['generated_events'],r['quorum_decisions'])==exp[:2]
        _close(round(r['mean_ambiguity_reduction_pp'],2),exp[2],1e-9)
        _close(round(r['max_ambiguity_reduction_pp'],2),exp[3],1e-9)
        assert r['robust_resolved_errors']==exp[4]

    # Independent exhaustive oracle audit of the exact attainable count set.
    oracle=_j('exact_oracle_validation.summary.json')
    assert oracle['n_instances']==30_000
    assert oracle['feasible_instances']==24_708
    assert oracle['infeasible_instances']==5_292
    assert oracle['match_count']==30_000
    assert oracle['mismatch_count']==0
    assert oracle['extrema_match_count']==30_000
    assert oracle['extrema_mismatch_count']==0
    assert oracle['all_instances_match'] is True
    assert oracle.get('production_imports')==['robust_coupled_quorum_count_set','robust_coupled_quorum_classification']

    # Independent exhaustive audit of the nonnegative weighted-score extension.
    woracle=_j('weighted_oracle_validation.summary.json')
    assert woracle['n_instances']==20_000
    assert woracle['match_count']==20_000
    assert woracle['mismatch_count']==0
    assert woracle['all_instances_match'] is True

    # ASPA daily snapshot differencing and pilot candidate table.
    changes=_j('aspa_changes_2026-08-26_09-02.json')
    modified=[e for e in changes['events'] if not e['customer_created'] and not e['customer_deleted']]
    assert len(modified)==66
    assert sum(len(e['providers_added']) for e in modified)==64
    assert sum(len(e['providers_removed']) for e in modified)==28

    with (IN/'pilot_signing_time_probe_1h.csv').open(newline='',encoding='utf-8') as h:
        rows=list(csv.DictReader(h))
    positives=[r for r in rows if r.get('exact_status') in POS]
    assert len(positives)==12
    assert sum(r['change']=='added' for r in positives)==9
    assert sum(r['change']=='removed' for r in positives)==3
    assert len({int(r['customer']) for r in positives})==12
    assert len({int(r['provider']) for r in positives})==8

    bracket=_j('pilot_bracket_reclassification_1h.json')
    assert bracket['signing_time_candidate_rows']==12
    assert bracket['daily_snapshot_bracket_definite_gap']==0
    assert bracket['daily_snapshot_bracket_timing_ambiguous']==12
    assert bracket['daily_snapshot_bracket_no_gap']==0
    _close(round(bracket['decision_resolution_margin_hours_median'],2),6.02,1e-9)
    _close(round(bracket['decision_resolution_margin_hours_min'],2),0.23,1e-9)
    _close(round(bracket['decision_resolution_margin_hours_max'],2),10.52,1e-9)
    assert bracket['ambiguous_within_1h_of_endpoint']==1
    assert bracket['ambiguous_within_4h_of_endpoint']==2
    assert bracket['ambiguous_within_6h_of_endpoint']==5
    assert bracket['ambiguous_within_8h_of_endpoint']==8
    assert bracket['ambiguous_within_12h_of_endpoint']==12
    from datetime import datetime
    assert len(bracket['rows'])==12
    for r in bracket['rows']:
        assert datetime.fromisoformat(r['snapshot_before_utc']) < datetime.fromisoformat(r['probe_time_utc']) < datetime.fromisoformat(r['snapshot_after_utc'])

    print('REPORTED_RESULTS=PASS')

if __name__=='__main__':
    main()
