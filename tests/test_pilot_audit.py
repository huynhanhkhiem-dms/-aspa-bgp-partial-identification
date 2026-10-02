import csv, json
from pathlib import Path
from classify_pilot_bracket_evidence import summarize as bracket_summary
from diff_aspa_timeseries import effective_providers

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data'/'input'
OUTPUT=ROOT/'data'/'output'
POS={"route_observed_before_embedded_signing_time","route_observed_after_embedded_signing_time"}


def _candidate_rows():
    with (INPUT/'pilot_signing_time_probe_1h.csv').open(newline='',encoding='utf-8') as h:
        return list(csv.DictReader(h))


def _changes():
    return json.loads((OUTPUT/'aspa_changes_2026-08-26_09-02.json').read_text())


def test_snapshot_diff_denominators():
    p=_changes()
    modified=[e for e in p['events'] if not e['customer_created'] and not e['customer_deleted']]
    assert len(modified)==66
    assert sum(len(e['providers_added']) for e in modified)==64
    assert sum(len(e['providers_removed']) for e in modified)==28


def test_candidate_counts_and_distinct_entities():
    rows=[r for r in _candidate_rows() if r['exact_status'] in POS]
    assert len(rows)==12
    assert sum(r['change']=='added' for r in rows)==9
    assert sum(r['change']=='removed' for r in rows)==3
    assert len({int(r['customer']) for r in rows})==12
    assert len({int(r['provider']) for r in rows})==8


def test_signing_time_candidates_are_ambiguous_under_daily_snapshot_brackets():
    s=bracket_summary(_candidate_rows())
    assert s['signing_time_candidate_rows']==12
    assert s['daily_snapshot_bracket_definite_gap']==0
    assert s['daily_snapshot_bracket_timing_ambiguous']==12
    assert s['daily_snapshot_bracket_no_gap']==0


def test_every_candidate_probe_is_strictly_inside_daily_bracket():
    from datetime import datetime
    s=bracket_summary(_candidate_rows())
    assert len(s['rows'])==12
    for r in s['rows']:
        before=datetime.fromisoformat(r['snapshot_before_utc'])
        probe=datetime.fromisoformat(r['probe_time_utc'])
        after=datetime.fromisoformat(r['snapshot_after_utc'])
        assert before < probe < after
