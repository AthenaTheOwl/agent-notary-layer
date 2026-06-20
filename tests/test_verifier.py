"""Unit tests for canonical, schema, key, signature, and chain logic."""

from __future__ import annotations

import base64
import json
import pathlib
import urllib.parse

import pytest

from notary import verifier as v
from notary.canonical import canonicalize, signed_bytes
from notary.verifier import (
    BadCanonicalHashFormat,
    ChainBreak,
    ChainNoRoot,
    ChainNotLinear,
    CycleDetected,
    FileKeyResolver,
    KeyMalformed,
    SchemaInvalid,
    SignatureInvalid,
    UnknownSigner,
    load_schema,
    order_and_check,
    validate,
    verify_receipt,
    verify_signature,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFORMANCE = REPO_ROOT / "conformance"


# --- canonical (JCS) ---------------------------------------------------------


def test_canonicalize_primitives():
    assert canonicalize(None) == b"null"
    assert canonicalize(True) == b"true"
    assert canonicalize(False) == b"false"
    assert canonicalize(0) == b"0"
    assert canonicalize(42) == b"42"
    assert canonicalize("hello") == b'"hello"'


def test_canonicalize_object_sorts_keys():
    out = canonicalize({"b": 2, "a": 1, "c": 3})
    assert out == b'{"a":1,"b":2,"c":3}'


def test_canonicalize_escapes_required_chars_only():
    out = canonicalize({"k": 'he said "hi"\n'})
    assert out == b'{"k":"he said \\"hi\\"\\n"}'


def test_canonicalize_array_preserves_order():
    assert canonicalize([3, 1, 2]) == b"[3,1,2]"


def test_signed_bytes_omits_signature_field():
    receipt = {"a": 1, "signature": "ignored", "b": 2}
    assert signed_bytes(receipt) == b'{"a":1,"b":2}'


# --- schema -----------------------------------------------------------------


def test_load_schema_returns_dict_with_id():
    schema = load_schema()
    assert schema["$id"] == "https://notary.example/schema/agent-receipt/v0.1.json"
    assert schema["additionalProperties"] is False


def test_validate_accepts_conformance_positive_minimal():
    data = json.loads((CONFORMANCE / "positive" / "minimal.json").read_text())
    validate(data)


@pytest.mark.parametrize(
    "fixture",
    [
        "missing-signature.json",
        "extra-field.json",
        "bad-ulid.json",
        "bad-timestamp.json",
        "wrong-algorithm.json",
    ],
)
def test_validate_rejects_negative_fixtures(fixture: str):
    data = json.loads((CONFORMANCE / "negative" / fixture).read_text())
    with pytest.raises(SchemaInvalid):
        validate(data)


def test_validate_routes_hash_only_failure_to_distinct_error():
    data = json.loads((CONFORMANCE / "negative" / "bad-hash-format.json").read_text())
    with pytest.raises(BadCanonicalHashFormat):
        validate(data)


# --- file key resolver ------------------------------------------------------


def test_file_key_resolver_resolves_known_identity(keys_dir, signing_key):
    resolver = FileKeyResolver(keys_dir)
    key = resolver.resolve("did:web:example.test/agents/buyer-1")
    assert key == bytes(signing_key.verify_key)
    assert len(key) == 32


def test_file_key_resolver_raises_unknown_signer(tmp_path):
    resolver = FileKeyResolver(tmp_path / "keys")
    with pytest.raises(UnknownSigner):
        resolver.resolve("did:web:nope")


def test_file_key_resolver_raises_key_malformed_on_wrong_length(tmp_path):
    d = tmp_path / "keys"
    d.mkdir()
    fname = urllib.parse.quote("did:web:short", safe="") + ".pub"
    (d / fname).write_text(base64.b64encode(b"only-eight").decode(), encoding="utf-8")
    resolver = FileKeyResolver(d)
    with pytest.raises(KeyMalformed):
        resolver.resolve("did:web:short")


def test_file_key_resolver_percent_encodes_did(tmp_path, pubkey_b64):
    d = tmp_path / "keys"
    d.mkdir()
    identity = "did:web:example.test/agents/x"
    encoded = urllib.parse.quote(identity, safe="")
    assert "%3A" in encoded and "%2F" in encoded
    (d / f"{encoded}.pub").write_text(pubkey_b64, encoding="utf-8")
    resolver = FileKeyResolver(d)
    key = resolver.resolve(identity)
    assert len(key) == 32


# --- signature --------------------------------------------------------------


def test_verify_signature_accepts_real_signature(signing_key):
    msg = b"hello world"
    sig = base64.b64encode(signing_key.sign(msg).signature).decode()
    verify_signature(bytes(signing_key.verify_key), msg, sig)


def test_verify_signature_rejects_tampered_message(signing_key):
    sig = base64.b64encode(signing_key.sign(b"a").signature).decode()
    with pytest.raises(SignatureInvalid):
        verify_signature(bytes(signing_key.verify_key), b"b", sig)


def test_verify_signature_rejects_wrong_length_signature(signing_key):
    sig = base64.b64encode(b"too short").decode()
    with pytest.raises(SignatureInvalid):
        verify_signature(bytes(signing_key.verify_key), b"x", sig)


# --- full receipt verification ----------------------------------------------


def test_verify_receipt_accepts_freshly_signed(make_signed_receipt, keys_dir):
    receipt = make_signed_receipt()
    resolver = FileKeyResolver(keys_dir)
    verify_receipt(receipt, resolver)


def test_verify_receipt_rejects_tampered_hash(make_signed_receipt, keys_dir):
    receipt = make_signed_receipt()
    receipt["action_canonical_hash"] = "sha256:" + "b" * 64
    resolver = FileKeyResolver(keys_dir)
    with pytest.raises(SignatureInvalid):
        verify_receipt(receipt, resolver)


def test_verify_receipt_unknown_signer(make_signed_receipt, tmp_path):
    receipt = make_signed_receipt()
    resolver = FileKeyResolver(tmp_path / "keys-empty")
    with pytest.raises(UnknownSigner):
        verify_receipt(receipt, resolver)


# --- chain ------------------------------------------------------------------


def _three_chain(make_signed_receipt) -> list[dict]:
    r1 = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id=None,
        timestamp="2026-07-04T14:22:31Z",
    )
    r2 = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        timestamp="2026-07-04T14:22:32Z",
    )
    r3 = make_signed_receipt(
        receipt_id="01J7Z9PM4Q2X3F0K0F0A0J3T20",
        prior_receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        timestamp="2026-07-04T14:22:33Z",
    )
    return [r1, r2, r3]


def test_order_and_check_linear_three(make_signed_receipt):
    chain = _three_chain(make_signed_receipt)
    ordered = order_and_check(list(reversed(chain)))
    ids = [r["receipt_id"] for r in ordered]
    assert ids == [c["receipt_id"] for c in chain]


def test_order_and_check_two_roots(make_signed_receipt):
    a = make_signed_receipt(receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y")
    b = make_signed_receipt(receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z")
    with pytest.raises(ChainNotLinear):
        order_and_check([a, b])


def test_order_and_check_cycle_detected(make_signed_receipt):
    # Two-node cycle: A.prior=B and B.prior=A. Detected before root check.
    a = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
    )
    b = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
    )
    with pytest.raises(CycleDetected):
        order_and_check([a, b])


def test_order_and_check_no_root_chain_to_missing(make_signed_receipt):
    # All receipts point to a missing predecessor → no root with prior=null.
    a = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id="01J7Z9PM4Z2X3F0K0F0A0J3T20",  # missing
    )
    with pytest.raises(ChainNoRoot):
        order_and_check([a])


def test_order_and_check_break(make_signed_receipt):
    a = make_signed_receipt(receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y", prior_receipt_id=None)
    b = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4Q2X3F0K0F0A0J3T20",
    )
    with pytest.raises(ChainBreak):
        order_and_check([a, b])


def test_order_and_check_fork_is_not_linear(make_signed_receipt):
    root = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y", prior_receipt_id=None
    )
    child1 = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
    )
    child2 = make_signed_receipt(
        receipt_id="01J7Z9PM4Q2X3F0K0F0A0J3T20",
        prior_receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
    )
    with pytest.raises(ChainNotLinear):
        order_and_check([root, child1, child2])


def test_reject_codes_match_design_table():
    assert v.REJECT_CODES == {
        "schema_invalid": 2,
        "bad_canonical_hash_format": 3,
        "unknown_signer": 4,
        "signature_invalid": 5,
        "chain_not_linear": 6,
        "chain_break": 7,
        "chain_no_root": 8,
        "cycle_detected": 9,
        "key_malformed": 10,
    }
