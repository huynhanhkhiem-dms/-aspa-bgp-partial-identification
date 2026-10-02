import pytest
from aspa_semantics import (
    AuthorizationState, InvalidSPAS, UnsupportedASPath, UspasState,
    authorization_state, build_usp_as_states, compress_as_path,
    has_ordered_adjacent_edge, has_origin_adjacent_edge, merge_spas,
    normalize_authorization_state, parse_strict_bool, validate_spas,
)


def test_prepend_compression_and_edge():
    assert compress_as_path([64500, 64496, 64496, 64497]) == [64500, 64496, 64497]
    assert has_origin_adjacent_edge([64500, 64496, 64496, 64497], 64497, 64496)


def test_ordered_adjacent_edge_can_be_internal():
    path=[64510,64500,64497,64480]
    assert has_ordered_adjacent_edge(path,64497,64500)
    assert not has_origin_adjacent_edge(path,64497,64500)


def test_non_sequence_is_rejected():
    with pytest.raises(UnsupportedASPath):
        compress_as_path([64500, "{64496,64497}", 64498])


def test_usp_as_union_and_as0_rule_across_objects():
    providers, as0 = merge_spas([[0], [64500, 64501]])
    assert providers == frozenset({64500, 64501})
    assert not as0
    providers, as0 = merge_spas([[0], [0]])
    assert providers == frozenset({0})
    assert as0


def test_duplicate_customer_objects_are_merged_not_overwritten():
    states = build_usp_as_states([
        {"date":"2026-01-01","customer":65000,"providers":[64500],"tal":"arin"},
        {"date":"2026-01-01","customer":65000,"providers":[64501],"tal":"ripencc"},
    ])
    s=states["2026-01-01"][65000]
    assert s.providers == frozenset({64500,64501})
    assert s.object_count == 2
    assert s.tals == ("arin","ripencc")


def test_as_sequence_rejects_as0_and_out_of_range_asn():
    for bad in (0, "0", "AS0", 4294967296, "4294967296", "AS4294967296"):
        with pytest.raises(UnsupportedASPath):
            compress_as_path([64500, bad, 64501])


def test_as_sequence_accepts_max_32_bit_asn():
    assert compress_as_path([4294967295]) == [4294967295]


def test_strict_boolean_parser_rejects_unknown():
    assert parse_strict_bool("true") is True
    assert parse_strict_bool("0") is False
    with pytest.raises(ValueError): parse_strict_bool("unknown")


def test_authorization_state_is_tri_state():
    assert normalize_authorization_state("Provider+") == AuthorizationState.PROVIDER_PLUS
    assert normalize_authorization_state("Not Provider+") == AuthorizationState.NOT_PROVIDER_PLUS
    assert normalize_authorization_state("No Attestation") == AuthorizationState.NO_ATTESTATION
    with pytest.raises(ValueError): normalize_authorization_state("unauthorized")


def test_provider_authorization_distinguishes_no_attestation():
    s=UspasState(frozenset({64500}),False,1,("arin",))
    assert authorization_state(s,64500)==AuthorizationState.PROVIDER_PLUS
    assert authorization_state(s,64501)==AuthorizationState.NOT_PROVIDER_PLUS
    assert authorization_state(None,64500)==AuthorizationState.NO_ATTESTATION


@pytest.mark.parametrize("providers", [[], [64500,64500], [0,64500], [65000], [4294967296]])
def test_invalid_spas_is_rejected(providers):
    with pytest.raises(InvalidSPAS):
        validate_spas(providers, customer=65000)


def test_unsorted_spas_is_rejected():
    with pytest.raises(InvalidSPAS): validate_spas([64501,64500], customer=65000)


def test_as0_only_spas_is_valid_and_not_provider_plus_for_real_provider():
    vals=validate_spas([0],customer=65000)
    providers,as0=merge_spas([vals],customer=65000)
    s=UspasState(providers,as0,1,("arin",))
    assert authorization_state(s,64500)==AuthorizationState.NOT_PROVIDER_PLUS
