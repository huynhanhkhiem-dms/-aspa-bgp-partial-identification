#!/usr/bin/env python3
"""Build a deterministic cross-vantage global ASPA transition lineage.

Production use requires every clean per-vantage transition to carry a stable
``source_change_key`` emitted by the RPKI decoder.  The key MUST identify one
canonical repository/content transition (for example, repository identity +
customer + previous/current object hashes or equivalent serialised publication
identity).  We deliberately do not infer global events by calendar day or by
(customer, provider) alone because repeated add/remove/add cycles would then be
ambiguous.

Rows sharing the same source_change_key, customer, provider and direction map to
one ``global_event_id``.  Any disagreement is a hard error.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

PRIMARY = {"added", "removed"}


def _event_id(source_change_key: str, customer: int, provider: int, direction: str) -> str:
    material = f"{source_change_key}|{customer}|{provider}|{direction}".encode("utf-8")
    return "ge_" + hashlib.sha256(material).hexdigest()[:20]


def build_global_event_lineage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    seen_local: set[str] = set()
    for row in rows:
        if str(row.get("primary_provider_pair_transition", "")).strip().lower() not in {"1","true","yes","y"}:
            continue
        direction = str(row.get("change", "")).strip()
        if direction not in PRIMARY:
            continue
        if str(row.get("clean_adjacent_covered_transition", "")).strip().lower() not in {"1","true","yes","y"}:
            continue
        source_key = str(row.get("source_change_key", "")).strip()
        if not source_key:
            raise ValueError("global lineage requires non-empty source_change_key on every clean primary transition")
        local_id = str(row.get("transition_id", "")).strip()
        if not local_id:
            raise ValueError("transition_id is required")
        if local_id in seen_local:
            raise ValueError(f"duplicate transition_id: {local_id}")
        seen_local.add(local_id)
        key = (source_key, int(row["customer"]), int(row["provider"]), direction)
        groups[key].append(row)

    out: list[dict[str, Any]] = []
    for (source_key, customer, provider, direction), members in sorted(groups.items()):
        gid = _event_id(source_key, customer, provider, direction)
        vantages = {str(r["vantage"]) for r in members}
        for r in sorted(members, key=lambda x: (str(x["vantage"]), str(x["transition_id"]))):
            out.append({
                "global_event_id": gid,
                "source_change_key": source_key,
                "customer": customer,
                "provider": provider,
                "event_direction": direction,
                "rpki_vantage": str(r["vantage"]),
                "rpki_transition_id": str(r["transition_id"]),
                "transition_left_observation": str(r.get("transition_left_observation", "")),
                "transition_right_observation": str(r.get("transition_right_observation", "")),
                "supporting_rpki_vantage_count": len(vantages),
                "lineage_semantics": "exact_source_change_key_not_calendar_or_pair_clustering",
            })
    return out


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("transitions", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = build_global_event_lineage(_read(args.transitions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else [
        "global_event_id","source_change_key","customer","provider","event_direction",
        "rpki_vantage","rpki_transition_id","transition_left_observation",
        "transition_right_observation","supporting_rpki_vantage_count","lineage_semantics",
    ]
    with args.output.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"mapped_transition_rows={len(rows)} global_events={len({r['global_event_id'] for r in rows})}")


if __name__ == "__main__":
    main()
