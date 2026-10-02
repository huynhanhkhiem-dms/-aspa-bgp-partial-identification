#!/usr/bin/env python3
"""Compute day-to-day effective ASPA provider transitions in the pilot snapshot series.

The packaged snapshot extraction is already an RP/TAL-level provider view, not
raw ASN.1 ASPA eContent.  A row may therefore contain AS0 together with nonzero
providers after upstream merging.  Profile-29 section 5.2 requires AS0 to be
removed from an effective U-SPAS whenever any nonzero provider is present.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ASN_MAX = 0xFFFFFFFF


@dataclass(frozen=True)
class SnapshotState:
    providers: frozenset[int]
    source_rows: int
    tals: tuple[str, ...]


def _normalize_effective_providers(values, customer: int) -> set[int]:
    vals=[int(x) for x in values]
    if any(x < 0 or x > ASN_MAX for x in vals):
        raise ValueError("provider ASN outside 0..2^32-1")
    if customer in vals:
        raise ValueError("customer ASN appears in provider set")
    providers=set(vals)
    nonzero={x for x in providers if x != 0}
    return nonzero if nonzero else ({0} if 0 in providers else set())


def build_snapshot_states(rows: list[dict]) -> dict[str, dict[int, SnapshotState]]:
    grouped: dict[tuple[str,int], list[dict]]={}
    for row in rows:
        grouped.setdefault((str(row['date']),int(row['customer'])),[]).append(row)
    out: dict[str,dict[int,SnapshotState]]={}
    for (date,customer),items in grouped.items():
        merged:set[int]=set()
        for row in items:
            merged.update(_normalize_effective_providers(row.get('providers',[]),customer))
        nonzero={x for x in merged if x != 0}
        effective=nonzero if nonzero else ({0} if 0 in merged else set())
        out.setdefault(date,{})[customer]=SnapshotState(
            providers=frozenset(effective),
            source_rows=len(items),
            tals=tuple(sorted({str(x.get('tal','')) for x in items})),
        )
    return out


def effective_providers(state: SnapshotState | None) -> set[int]:
    if state is None:
        return set()
    return {asn for asn in state.providers if asn != 0}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    payload=json.loads(args.input.read_text(encoding='utf-8'))
    states=build_snapshot_states(payload['aspas'])
    dates=sorted(states)
    events=[]; transitions=[]
    for before_date,after_date in zip(dates,dates[1:]):
        before,after=states[before_date],states[after_date]
        day=[]
        for customer in sorted(before.keys()|after.keys()):
            old_state,new_state=before.get(customer),after.get(customer)
            old,new=effective_providers(old_state),effective_providers(new_state)
            added,removed=sorted(new-old),sorted(old-new)
            if added or removed or old_state is None or new_state is None:
                day.append({
                    'date_before':before_date,'date_after':after_date,'customer':customer,
                    'providers_before':sorted(old),'providers_after':sorted(new),
                    'providers_added':added,'providers_removed':removed,
                    'customer_created':old_state is None,'customer_deleted':new_state is None,
                    'as0_only_before':bool(old_state and old_state.providers==frozenset({0})),
                    'as0_only_after':bool(new_state and new_state.providers==frozenset({0})),
                    'object_count_before':old_state.source_rows if old_state else 0,
                    'object_count_after':new_state.source_rows if new_state else 0,
                    'tals_before':list(old_state.tals) if old_state else [],
                    'tals_after':list(new_state.tals) if new_state else [],
                })
        events.extend(day)
        modified=[e for e in day if not e['customer_created'] and not e['customer_deleted']]
        transitions.append({
            'date_before':before_date,'date_after':after_date,
            'customers_before':len(before),'customers_after':len(after),
            'changed_customers':len(day),'modified_customers':len(modified),
            'modified_provider_additions':sum(len(e['providers_added']) for e in modified),
            'modified_provider_removals':sum(len(e['providers_removed']) for e in modified),
        })
    result={
        'semantics':{
            'state':'effective U-SPAS union per draft-ietf-sidrops-aspa-profile-29 section 5.2',
            'as0':'remove AS0 when any nonzero provider exists in the effective union',
            'created_deleted':'retained in audit; excluded from provider-modification denominator',
            'input_level':'archived RP/TAL-level provider extraction; not raw ASN.1 eContent',
        },
        'dates':dates,'transitions':transitions,'events':events,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding='utf-8')
    print(json.dumps(transitions,indent=2))


if __name__=='__main__':
    main()
