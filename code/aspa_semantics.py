#!/usr/bin/env python3
"""Protocol-grounded helpers shared by the ASPA measurement pipeline.

The active helpers implement the ASPA profile/verification semantics used by
this artifact:

* each decoded SPAS must satisfy profile constraints before it is admitted;
* U-SPAS is the union of simultaneously valid SPAS values for one customer;
* AS0 is an ASPA sentinel and is not a legal BGP AS_SEQUENCE ASN;
* provider authorization is tri-state: Provider+, Not Provider+, or
  No Attestation;
* COMPRESSED_AS_PATH removes consecutive duplicate ASNs before edge tests.

The helpers deliberately keep observed provider-edge evidence distinct from
full draft-v28 AS_PATH verification outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Sequence

ASN_MAX = 0xFFFFFFFF
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n"}


class UnsupportedASPath(ValueError):
    """Raised when a lightweight path cannot safely be interpreted as AS_SEQUENCE."""


class InvalidSPAS(ValueError):
    """Raised when a decoded SPAS violates active profile constraints."""


class AuthorizationState(str, Enum):
    PROVIDER_PLUS = "Provider+"
    NOT_PROVIDER_PLUS = "Not Provider+"
    NO_ATTESTATION = "No Attestation"


def parse_strict_bool(value: Any, *, field: str = "boolean") -> bool:
    """Parse an explicit boolean token; unknown/malformed values fail fast."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"{field} must be an explicit boolean token, got {value!r}")


def normalize_authorization_state(value: Any) -> AuthorizationState:
    """Normalize the draft-v28 provider-authorization function output."""
    if isinstance(value, AuthorizationState):
        return value
    text = str(value).strip().lower().replace("_", " ")
    aliases = {
        "provider+": AuthorizationState.PROVIDER_PLUS,
        "provider plus": AuthorizationState.PROVIDER_PLUS,
        "not provider+": AuthorizationState.NOT_PROVIDER_PLUS,
        "not provider plus": AuthorizationState.NOT_PROVIDER_PLUS,
        "no attestation": AuthorizationState.NO_ATTESTATION,
    }
    if text not in aliases:
        raise ValueError(f"unsupported authorization state: {value!r}")
    return aliases[text]


def row_authorization_state(row: dict[str, Any]) -> AuthorizationState:
    """Read primary ``auth_state`` or an explicitly legacy binary row.

    Legacy ``authorized`` is supported only for archived/regression fixtures:
    true -> Provider+, false -> Not Provider+. It can never express
    No Attestation and should not be used by a production decoder.
    """
    if "auth_state" in row and str(row.get("auth_state", "")).strip():
        return normalize_authorization_state(row["auth_state"])
    if "authorized" in row:
        return (
            AuthorizationState.PROVIDER_PLUS
            if parse_strict_bool(row["authorized"], field="authorized")
            else AuthorizationState.NOT_PROVIDER_PLUS
        )
    raise ValueError("RPKI row must contain auth_state; legacy authorized is accepted only for archived fixtures")


def _asn(value: Any) -> int:
    if isinstance(value, bool):
        raise UnsupportedASPath("boolean is not an ASN")
    if isinstance(value, int):
        if not (1 <= value <= ASN_MAX):
            raise UnsupportedASPath("AS_SEQUENCE ASN must be in 1..4294967295")
        return value
    if isinstance(value, str):
        text = value.strip()
        if any(token in text for token in ("{", "}", "(", ")", "[", "]", ",")):
            raise UnsupportedASPath(f"non-AS_SEQUENCE segment: {value!r}")
        if text.upper().startswith("AS"):
            text = text[2:]
        if text.isdigit():
            asn = int(text)
            if not (1 <= asn <= ASN_MAX):
                raise UnsupportedASPath("AS_SEQUENCE ASN must be in 1..4294967295")
            return asn
    raise UnsupportedASPath(f"unsupported AS path element: {value!r}")


def compress_as_path(path: Sequence[Any]) -> list[int]:
    """Parse an AS_SEQUENCE-like path and remove consecutive duplicate ASNs."""
    out: list[int] = []
    for raw in path:
        if isinstance(raw, (list, tuple, set, dict)):
            raise UnsupportedASPath(f"structured AS path segment: {raw!r}")
        asn = _asn(raw)
        if not out or out[-1] != asn:
            out.append(asn)
    return out


def has_origin_adjacent_edge(path: Sequence[Any], customer: int, provider: int) -> bool:
    """Return True iff compressed path terminates ``... provider, customer``."""
    compressed = compress_as_path(path)
    return len(compressed) >= 2 and compressed[-1] == customer and compressed[-2] == provider


def has_ordered_adjacent_edge(path: Sequence[Any], customer: int, provider: int) -> bool:
    """Return True iff compressed AS_SEQUENCE contains ``provider, customer`` anywhere."""
    compressed = compress_as_path(path)
    return any(a == provider and b == customer for a, b in zip(compressed, compressed[1:]))


def validate_spas(providers: Iterable[Any], *, customer: int | None = None, require_sorted: bool = True) -> tuple[int, ...]:
    """Validate one decoded SPAS against profile-29 content constraints.

    A SPAS must be non-empty, contain unique PAS values in 0..2^32-1, not
    contain the customer ASN, and AS0 may only appear as the sole element.
    Decoded provider order is checked because DER/profile input is ordered.
    """
    vals: list[int] = []
    for raw in providers:
        if isinstance(raw, bool):
            raise InvalidSPAS("boolean is not a PAS")
        try:
            val = int(raw)
        except (TypeError, ValueError) as exc:
            raise InvalidSPAS(f"invalid PAS value {raw!r}") from exc
        if not (0 <= val <= ASN_MAX):
            raise InvalidSPAS(f"PAS out of range: {val}")
        vals.append(val)
    if not vals:
        raise InvalidSPAS("ProviderASSet must contain at least one PAS")
    if len(set(vals)) != len(vals):
        raise InvalidSPAS("ProviderASSet contains duplicate PAS values")
    if require_sorted and vals != sorted(vals):
        raise InvalidSPAS("ProviderASSet must be sorted in ascending numerical order")
    if customer is not None and int(customer) in vals:
        raise InvalidSPAS("customerASID must not appear in ProviderASSet")
    if 0 in vals and vals != [0]:
        raise InvalidSPAS("AS0 may only appear as the sole PAS in one SPAS")
    return tuple(vals)


@dataclass(frozen=True)
class UspasState:
    providers: frozenset[int]
    has_as0_only: bool
    object_count: int
    tals: tuple[str, ...]


def merge_spas(
    provider_sets: Iterable[Iterable[Any]],
    *,
    customer: int | None = None,
    require_sorted: bool = True,
) -> tuple[frozenset[int], bool]:
    """Merge validated SPAS sets into U-SPAS.

    Multiple valid objects are unioned for robustness/transition handling.
    If any non-zero provider exists in the union, AS0 has no influence and is
    removed from the effective U-SPAS.
    """
    union: set[int] = set()
    count = 0
    for providers in provider_sets:
        count += 1
        union.update(validate_spas(providers, customer=customer, require_sorted=require_sorted))
    if count == 0:
        raise ValueError("merge_spas requires at least one valid ASPA object")
    nonzero = {x for x in union if x != 0}
    if nonzero:
        return frozenset(nonzero), False
    return frozenset({0}), True


def authorization_state(usp_as: UspasState | None, provider: int) -> AuthorizationState:
    """Evaluate draft-v28 provider authorization for one ordered CAS/PAS pair."""
    if usp_as is None:
        return AuthorizationState.NO_ATTESTATION
    return (
        AuthorizationState.PROVIDER_PLUS
        if int(provider) in usp_as.providers
        else AuthorizationState.NOT_PROVIDER_PLUS
    )


def build_usp_as_states(rows: Iterable[dict]) -> dict[str, dict[int, UspasState]]:
    """Group snapshot rows by date/customer and merge duplicate valid ASPAs."""
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        grouped.setdefault((str(row["date"]), int(row["customer"])), []).append(row)
    states: dict[str, dict[int, UspasState]] = {}
    for (date, customer), objs in grouped.items():
        providers, has_as0_only = merge_spas(
            (obj.get("providers", []) for obj in objs), customer=customer, require_sorted=True
        )
        states.setdefault(date, {})[customer] = UspasState(
            providers=providers,
            has_as0_only=has_as0_only,
            object_count=len(objs),
            tals=tuple(sorted({str(obj.get("tal", "")) for obj in objs})),
        )
    return states
