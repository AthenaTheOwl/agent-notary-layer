#!/usr/bin/env python3
"""Regenerate conformance/usage/ and the payer's public key.

Signing keys come from `key_for` in make_delegation_fixtures.py: the same
synthetic, name-derived seed. They protect nothing and must never be used
outside this conformance suite. Only the public key is written.

The bundle is one billing period of three usage receipts from an answer
engine to a publisher. Two cite passages in the publisher's text; the third
cites a passage the publisher does not hold.

    python scripts/make_usage_fixtures.py
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from make_delegation_fixtures import key_for  # noqa: E402
from notary.canonical import canonicalize, signed_bytes  # noqa: E402
from notary.usage import action_canonical_hash, passage_sha256, split_passages  # noqa: E402

PAYER = "did:web:example.test/agents/answer-engine-1"
PAYEE = "did:web:example.test/publishers/press-1"
SOURCE = "press-1/harbor-notes"

CONTENT = """Harbor notes, autumn survey

The north channel holds four metres at low water from the breakwater to buoy 6.
Past buoy 6 the bottom rises to two and a half metres within forty metres.

Tidal range at the fuel dock averaged 3.1 metres across the survey. Spring
tides add half a metre at both ends.

The east slipway is closed to vessels over twelve metres until the ramp is
resurfaced.
"""

# Cited by the third receipt. It appears nowhere in CONTENT.
NOT_HELD = "The south channel was dredged to six metres in the spring."


def usage(passage: str, answer_id: str) -> dict:
    return {
        "kind": "usage",
        "passage_sha256": passage_sha256(passage),
        "answer_id": answer_id,
        "source_id": SOURCE,
    }


def receipt(receipt_id: str, prior: str | None, action: dict, timestamp: str) -> dict:
    body = {
        "receipt_id": receipt_id,
        "prior_receipt_id": prior,
        "action_canonical_hash": action_canonical_hash(action),
        "sender_identity": PAYER,
        "receiver_identity": PAYEE,
        "timestamp": timestamp,
        "signature_algorithm": "ed25519",
    }
    sig = key_for(PAYER).sign(signed_bytes(body)).signature
    body["signature"] = base64.b64encode(sig).decode("ascii")
    return body


def build(root: pathlib.Path) -> None:
    """Write conformance/usage/ and the payer's .pub under `root`."""
    usage_dir = root / "conformance" / "usage"
    content_dir = usage_dir / "content"
    period = usage_dir / "billing-period-01"
    for d in (content_dir, period, root / "keys"):
        d.mkdir(parents=True, exist_ok=True)
    for old in period.glob("*.json"):
        old.unlink()

    (content_dir / "harbor-notes.txt").write_text(CONTENT, encoding="utf-8", newline="\n")

    passages = split_passages(CONTENT)
    actions = [
        usage(passages[1], "ans-0412"),
        usage(passages[2], "ans-0413"),
        usage(NOT_HELD, "ans-0414"),
    ]
    stamps = ["2026-10-01T08:14:00Z", "2026-10-03T16:40:00Z", "2026-10-06T11:02:00Z"]
    prior = None
    for i, (action, stamp) in enumerate(zip(actions, stamps), 1):
        r = receipt(f"01JA9000000000000000PAY{i:03d}", prior, action, stamp)
        (period / f"{i:02d}.json").write_text(
            json.dumps(r, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        prior = r["receipt_id"]
    (period / "actions.jsonl").write_text(
        "".join(canonicalize(a).decode("utf-8") + "\n" for a in actions),
        encoding="utf-8",
        newline="\n",
    )

    pub = base64.b64encode(bytes(key_for(PAYER).verify_key)).decode("ascii")
    (root / "keys" / (urllib.parse.quote(PAYER, safe="") + ".pub")).write_text(pub, encoding="utf-8")


def main() -> int:
    build(ROOT)
    print("wrote conformance/usage/{content,billing-period-01} and 1 key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
