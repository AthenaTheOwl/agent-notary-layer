#!/usr/bin/env python3
"""Regenerate conformance/delegation/ bundles and their public keys.

The signing seeds are synthetic and derived from each identity's name, so the
fixtures can be rebuilt byte-for-byte. They protect nothing and must never be
used outside this conformance suite.

    python scripts/make_delegation_fixtures.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
import urllib.parse

from nacl.signing import SigningKey

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notary.canonical import signed_bytes  # noqa: E402

PRINCIPAL = "did:web:example.test/agents/principal-1"
AGENT = "did:web:example.test/agents/agent-1"
OTHER_AGENT = "did:web:example.test/agents/agent-2"
TOOL = "did:web:example.test/tools/ledger-api"


def key_for(identity: str) -> SigningKey:
    return SigningKey(hashlib.sha256(b"notary-conformance-synthetic:" + identity.encode()).digest())


def receipt(receipt_id, prior, sender, receiver, action, timestamp, authorization=None) -> dict:
    body = {
        "receipt_id": receipt_id,
        "prior_receipt_id": prior,
        "action_canonical_hash": "sha256:" + hashlib.sha256(action.encode()).hexdigest(),
        "sender_identity": sender,
        "receiver_identity": receiver,
        "timestamp": timestamp,
        "signature_algorithm": "ed25519",
    }
    if authorization:
        body["authorization"] = authorization
    sig = key_for(sender).sign(signed_bytes(body)).signature
    body["signature"] = base64.b64encode(sig).decode("ascii")
    return body


def write_bundle(name: str, receipts: list[dict]) -> None:
    d = ROOT / "conformance" / "delegation" / name
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.json"):
        old.unlink()
    for i, r in enumerate(receipts, 1):
        (d / f"{i:02d}.json").write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    grant = receipt("01J8D0000000000000000GRNT1", None, PRINCIPAL, AGENT,
                    "grant: agent-1 may post ledger entries under 10,000 USD", "2026-09-23T09:00:00Z")
    hop = receipt("01J8D0000000000000000H0P01", grant["receipt_id"], AGENT, TOOL,
                  "post ledger entry 4,200 USD", "2026-09-23T09:05:00Z",
                  {"authorizing_receipt_id": grant["receipt_id"], "delegator_identity": PRINCIPAL})
    write_bundle("accept-two-hop", [grant, hop])

    # agent-2 cites a grant that was made to agent-1.
    stolen = receipt("01J8D0000000000000000H0P02", grant["receipt_id"], OTHER_AGENT, TOOL,
                     "post ledger entry 9,900 USD", "2026-09-23T09:06:00Z",
                     {"authorizing_receipt_id": grant["receipt_id"], "delegator_identity": PRINCIPAL})
    write_bundle("reject-wrong-grantee", [grant, stolen])

    # agent-1 cites a grant that is not in the bundle.
    orphan = receipt("01J8D0000000000000000H0P03", grant["receipt_id"], AGENT, TOOL,
                     "post ledger entry 50,000 USD", "2026-09-23T09:07:00Z",
                     {"authorizing_receipt_id": "01J8D0000000000000000GRNT9", "delegator_identity": PRINCIPAL})
    write_bundle("reject-missing-grant", [grant, orphan])

    for identity in (PRINCIPAL, AGENT, OTHER_AGENT):
        pub = base64.b64encode(bytes(key_for(identity).verify_key)).decode("ascii")
        (ROOT / "keys" / (urllib.parse.quote(identity, safe="") + ".pub")).write_text(pub, encoding="utf-8")
    print("wrote conformance/delegation/{accept-two-hop,reject-wrong-grantee,reject-missing-grant} and 3 keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
