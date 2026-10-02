import pytest
from build_global_event_lineage import build_global_event_lineage


def _transition(vantage, tid, key, change="added"):
    return {
        "vantage": vantage,
        "transition_id": tid,
        "source_change_key": key,
        "customer": 65000,
        "provider": 64500,
        "change": change,
        "primary_provider_pair_transition": True,
        "clean_adjacent_covered_transition": True,
        "transition_left_observation": "2026-01-01T00:00:00Z",
        "transition_right_observation": "2026-01-01T01:00:00Z",
    }


def test_same_source_change_key_maps_cross_vantage_to_one_global_event():
    out=build_global_event_lineage([_transition("r1","t1","repo:42"),_transition("r2","t2","repo:42")])
    assert len({r["global_event_id"] for r in out}) == 1
    assert {r["rpki_vantage"] for r in out} == {"r1","r2"}


def test_repeated_pair_events_do_not_merge_when_source_change_key_differs():
    out=build_global_event_lineage([_transition("r1","t1","repo:42"),_transition("r1","t2","repo:99")])
    assert len({r["global_event_id"] for r in out}) == 2


def test_missing_source_key_fails_closed():
    row=_transition("r1","t1","repo:42"); row["source_change_key"]=""
    with pytest.raises(ValueError): build_global_event_lineage([row])


def test_unclean_or_nonprimary_rows_are_not_promoted():
    a=_transition("r1","t1","repo:42"); a["clean_adjacent_covered_transition"]=False
    b=_transition("r1","t2","repo:43"); b["primary_provider_pair_transition"]=False
    assert build_global_event_lineage([a,b]) == []
