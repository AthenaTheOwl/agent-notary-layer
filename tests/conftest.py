"""Shared pytest fixtures: a deterministic test keypair and receipt builder."""

from __future__ import annotations

import base64
import json
import pathlib
import urllib.parse
from typing import Optional

import pytest
from nacl.signing import SigningKey

from notary.canonical import signed_bytes

TEST_SEED = b"notary-test-seed-32-bytes!!!!!!!"  # 32 bytes; synthetic, not secret.
TEST_SENDER = "did:web:example.test/agents/buyer-1"
TEST_RECEIVER = "did:web:example.test/agents/seller-1"


@pytest.fixture(scope="session")
def signing_key() -> SigningKey:
    assert len(TEST_SEED) == 32
    return SigningKey(TEST_SEED)


@pytest.fixture(scope="session")
def pubkey_b64(signing_key: SigningKey) -> str:
    return base64.b64encode(bytes(signing_key.verify_key)).decode("ascii")


@pytest.fixture
def keys_dir(tmp_path: pathlib.Path, pubkey_b64: str) -> pathlib.Path:
    d = tmp_path / "keys"
    d.mkdir()
    fname = urllib.parse.quote(TEST_SENDER, safe="") + ".pub"
    (d / fname).write_text(pubkey_b64, encoding="utf-8")
    return d


def make_receipt(
    signing_key: SigningKey,
    receipt_id: str = "01J7Z9PM4N2X3F0K0F0A0J3T1Y",
    prior_receipt_id: Optional[str] = None,
    sender: str = TEST_SENDER,
    receiver: str = TEST_RECEIVER,
    action_hash: str = "sha256:" + "a" * 64,
    timestamp: str = "2026-07-04T14:22:31Z",
) -> dict:
    unsigned = {
        "receipt_id": receipt_id,
        "prior_receipt_id": prior_receipt_id,
        "action_canonical_hash": action_hash,
        "sender_identity": sender,
        "receiver_identity": receiver,
        "timestamp": timestamp,
        "signature_algorithm": "ed25519",
    }
    sig = signing_key.sign(signed_bytes(unsigned)).signature
    unsigned["signature"] = base64.b64encode(sig).decode("ascii")
    return unsigned


@pytest.fixture
def make_signed_receipt(signing_key: SigningKey):
    def _factory(**kwargs) -> dict:
        return make_receipt(signing_key, **kwargs)

    return _factory


@pytest.fixture
def write_receipt(tmp_path: pathlib.Path):
    def _write(receipt: dict, name: str = "receipt.json") -> pathlib.Path:
        p = tmp_path / name
        p.write_text(json.dumps(receipt), encoding="utf-8")
        return p

    return _write
