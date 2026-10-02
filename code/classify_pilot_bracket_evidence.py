#!/usr/bin/env python3
"""Compute single-transition-conditional pilot sensitivity from covered snapshot brackets.

Daily snapshots do not exclude hidden intra-bracket reversals; outputs are
therefore resolution-sensitivity diagnostics, not unconditional sharp field
identification.
"""
from __future__ import annotations
import argparse, csv, json, statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from interval_identification import point_observation_classification, point_resolution_margin

POSITIVE={"route_observed_before_embedded_signing_time","route_observed_after_embedded_signing_time"}


def _ts(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def summarize(rows: list[dict]) -> dict:
    candidate=[r for r in rows if r.get('exact_status') in POSITIVE]
    labels=[]; detail=[]
    for r in candidate:
        direction='addition' if r['change']=='added' else 'removal'
        label=point_observation_classification(
            direction,
            _ts(r['snapshot_before_utc']),
            _ts(r['snapshot_after_utc']),
            _ts(r['probe_time_utc']),
        )
        labels.append(label)
        p=_ts(r['probe_time_utc']); l=_ts(r['snapshot_before_utc']); u=_ts(r['snapshot_after_utc'])
        margin_hours=point_resolution_margin(l,u,p)/3600.0
        detail.append({
            'customer':int(r['customer']),'provider':int(r['provider']),'change':r['change'],
            'probe_time_utc':r['probe_time_utc'],'snapshot_before_utc':r['snapshot_before_utc'],
            'snapshot_after_utc':r['snapshot_after_utc'],'bracket_classification':label,
            'decision_resolution_margin_hours':margin_hours,
        })
    counts=Counter(labels)
    margins=[r['decision_resolution_margin_hours'] for r in detail if r['bracket_classification']=='timing_ambiguous']
    return {
        'signing_time_candidate_rows':len(candidate),
        'daily_snapshot_bracket_definite_gap':counts['definite_gap'],
        'daily_snapshot_bracket_timing_ambiguous':counts['timing_ambiguous'],
        'daily_snapshot_bracket_no_gap':counts['no_gap'],
        'decision_resolution_margin_hours_median':statistics.median(margins) if margins else None,
        'decision_resolution_margin_hours_min':min(margins) if margins else None,
        'decision_resolution_margin_hours_max':max(margins) if margins else None,
        'ambiguous_within_1h_of_endpoint':sum(m<=1.0 for m in margins),
        'ambiguous_within_4h_of_endpoint':sum(m<=4.0 for m in margins),
        'ambiguous_within_6h_of_endpoint':sum(m<=6.0 for m in margins),
        'ambiguous_within_8h_of_endpoint':sum(m<=8.0 for m in margins),
        'ambiguous_within_12h_of_endpoint':sum(m<=12.0 for m in margins),
        'interpretation':'single-transition-conditional candidate diagnostics using daily brackets; embedded CMS signing time is not treated as transition time and hidden intra-bracket reversals are not excluded',
        'rows':detail,
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    with a.input.open(newline='',encoding='utf-8') as h: rows=list(csv.DictReader(h))
    out=summarize(rows); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding='utf-8'); print(json.dumps(out,sort_keys=True))

if __name__=='__main__': main()
