"""Delegated hops (RFC-001 §4a): committed bundles through the real CLI."""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

from notary import cli
from notary.verifier import REJECT_CODES

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLES = REPO_ROOT / "conformance" / "delegation"
KEYS_DIR = REPO_ROOT / "keys"


def _verify(directory: pathlib.Path) -> int:
    return cli.main(["verify-chain", str(directory), "--keys-dir", str(KEYS_DIR)])


@pytest.mark.parametrize(
    "bundle, expected",
    [
        ("accept-two-hop", 0),
        ("reject-wrong-grantee", REJECT_CODES["delegation_mismatch"]),
        ("reject-missing-grant", REJECT_CODES["delegation_missing"]),
    ],
)
def test_committed_bundles(bundle, expected, capsys):
    assert _verify(BUNDLES / bundle) == expected
    capsys.readouterr()


def test_authorization_is_covered_by_the_signature(tmp_path, capsys):
    bundle = tmp_path / "tampered"
    shutil.copytree(BUNDLES / "accept-two-hop", bundle)
    hop_path = bundle / "02.json"
    hop = json.loads(hop_path.read_text(encoding="utf-8"))
    hop["authorization"]["delegator_identity"] = "did:web:example.test/agents/agent-2"
    hop_path.write_text(json.dumps(hop), encoding="utf-8")
    assert _verify(bundle) == REJECT_CODES["signature_invalid"]
    capsys.readouterr()


def test_authorization_rejects_extra_fields(tmp_path, capsys):
    bundle = tmp_path / "extra"
    shutil.copytree(BUNDLES / "accept-two-hop", bundle)
    hop_path = bundle / "02.json"
    hop = json.loads(hop_path.read_text(encoding="utf-8"))
    hop["authorization"]["scope"] = "anything"
    hop_path.write_text(json.dumps(hop), encoding="utf-8")
    assert _verify(bundle) == REJECT_CODES["schema_invalid"]
    capsys.readouterr()
