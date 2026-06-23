"""End-to-end conformance: run the committed fixtures through the real
verifier with the committed keys/ directory.

These are the fixtures the README and `notary show`/`verify` commands
exercise, so the suite asserts the *documented* path actually works:
positives accept end-to-end (schema + signature), negatives reject, and
tampering a passing receipt is caught.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from notary import cli
from notary.verifier import FileKeyResolver, VerifyError, verify_receipt

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFORMANCE = REPO_ROOT / "conformance"
KEYS_DIR = REPO_ROOT / "keys"

POSITIVE = sorted((CONFORMANCE / "positive").glob("*.json"))
NEGATIVE = sorted((CONFORMANCE / "negative").glob("*.json"))


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixtures_and_keys_are_committed():
    assert POSITIVE, "no positive conformance fixtures found"
    assert NEGATIVE, "no negative conformance fixtures found"
    assert KEYS_DIR.is_dir(), "committed keys/ directory is missing"
    assert list(KEYS_DIR.glob("*.pub")), "no .pub key files committed"


@pytest.mark.parametrize("path", POSITIVE, ids=lambda p: p.name)
def test_positive_fixtures_verify_end_to_end(path: pathlib.Path):
    receipt = _load(path)
    verify_receipt(receipt, FileKeyResolver(KEYS_DIR))  # must not raise


@pytest.mark.parametrize("path", NEGATIVE, ids=lambda p: p.name)
def test_negative_fixtures_are_rejected(path: pathlib.Path):
    receipt = _load(path)
    with pytest.raises(VerifyError):
        verify_receipt(receipt, FileKeyResolver(KEYS_DIR))


@pytest.mark.parametrize("path", POSITIVE, ids=lambda p: p.name)
def test_tampering_a_positive_breaks_the_signature(path: pathlib.Path):
    receipt = _load(path)
    h = receipt["action_canonical_hash"]
    receipt["action_canonical_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
    with pytest.raises(VerifyError):
        verify_receipt(receipt, FileKeyResolver(KEYS_DIR))


def test_cli_verify_accepts_positive_minimal(capsys):
    path = CONFORMANCE / "positive" / "minimal.json"
    code = cli.main(["verify", str(path), "--keys-dir", str(KEYS_DIR)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.strip() == "accept"


def test_cli_verify_chain_accepts_positive_dir(capsys):
    code = cli.main(
        ["verify-chain", str(CONFORMANCE / "positive"), "--keys-dir", str(KEYS_DIR)]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "accept" in out


def test_cli_show_exits_zero_with_committed_assets(capsys):
    code = cli.main(["show"])
    out = capsys.readouterr().out
    assert code == 0
    assert "tamper detection working" in out
