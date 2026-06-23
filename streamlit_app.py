"""agent-notary-layer -- live demo (Streamlit Community Cloud).

Paste or select an agent receipt, verify it against the v0.1 schema and the
committed ed25519 keys, and see the chain + tamper result. No network, no
secrets: it runs the real reference verifier (src/notary/) over the committed
conformance fixtures and keys.

Deploy: Streamlit Community Cloud -> New app -> this repo, branch main,
main file streamlit_app.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

REPO = Path(__file__).resolve().parent
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from notary.verifier import (  # noqa: E402
    FileKeyResolver,
    VerifyError,
    order_and_check,
    verify_receipt,
)

CONF = REPO / "conformance"
KEYS = REPO / "keys"


def list_fixtures() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for sub, label in (("positive", "positive"), ("negative", "negative")):
        for p in sorted((CONF / sub).glob("*.json")):
            out[f"{label}/{p.name}"] = p
    return out


def verify_one(receipt: dict) -> tuple[bool, str]:
    try:
        verify_receipt(receipt, FileKeyResolver(KEYS))
    except VerifyError as e:
        return False, f"{e.code}: {e}"
    return True, "schema valid, signer known, ed25519 signature verified"


st.set_page_config(page_title="agent-notary-layer -- receipt verifier", layout="wide")
st.title("agent-notary-layer")
st.caption(
    "tamper-evident, receiver-attested receipts for cross-organization agent "
    "actions. paste or pick a receipt; the reference verifier checks the schema, "
    "resolves the signer key, and replays the ed25519 signature."
)

fixtures = list_fixtures()
if not fixtures:
    st.error("no conformance fixtures found under conformance/")
    st.stop()

mode = st.radio(
    "input",
    ["pick a committed fixture", "paste your own receipt JSON"],
    horizontal=True,
)

receipt_text = ""
if mode == "pick a committed fixture":
    choice = st.selectbox("fixture", list(fixtures), index=list(fixtures).index("positive/minimal.json") if "positive/minimal.json" in fixtures else 0)
    receipt_text = fixtures[choice].read_text(encoding="utf-8")
    st.code(receipt_text, language="json")
else:
    default = fixtures.get("positive/minimal.json")
    receipt_text = st.text_area(
        "receipt JSON",
        value=default.read_text(encoding="utf-8") if default else "{}",
        height=320,
    )

if st.button("verify", type="primary"):
    try:
        receipt = json.loads(receipt_text)
    except json.JSONDecodeError as e:
        st.error(f"not valid JSON: {e}")
        st.stop()

    accepted, reason = verify_one(receipt)
    if accepted:
        st.success(f"ACCEPT -- {reason}")
    else:
        st.error(f"REJECT -- {reason}")

    # Live tamper demonstration: flip one hex digit of the action hash.
    if isinstance(receipt, dict) and "action_canonical_hash" in receipt:
        tampered = dict(receipt)
        h = tampered["action_canonical_hash"]
        if isinstance(h, str) and h:
            tampered["action_canonical_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
            t_ok, t_reason = verify_one(tampered)
            with st.expander("tamper check (flip one hex digit of action_canonical_hash)"):
                if t_ok:
                    st.warning("tamper went UNDETECTED -- this should not happen")
                else:
                    st.info(f"tampered copy correctly REJECTED -- {t_reason}")

st.divider()
st.subheader("the committed chain")
st.caption("the three positive fixtures form one linear chain (root -> second -> third).")

chain_receipts = []
for name, p in fixtures.items():
    if name.startswith("positive/"):
        chain_receipts.append(json.loads(p.read_text(encoding="utf-8")))

try:
    ordered = order_and_check(chain_receipts)
    rows = []
    for r in ordered:
        ok, reason = verify_one(r)
        rows.append(
            {
                "receipt_id": r["receipt_id"][:12] + "...",
                "prior": (r.get("prior_receipt_id") or "(root)")[:12] + ("..." if r.get("prior_receipt_id") else ""),
                "sender": r["sender_identity"].rsplit("/", 1)[-1],
                "timestamp": r["timestamp"],
                "verify": "accept" if ok else "reject",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    st.success(f"chain verified: {len(ordered)} receipts, root-first, no breaks or cycles.")
except VerifyError as e:
    st.error(f"chain rejected -- {e.code}: {e}")

st.caption(
    "v0.1. schema: spec/agent-receipt.schema.json. verifier: src/notary/. "
    "run locally: `python -m notary show`. committed demo keys are synthetic, not secret."
)
