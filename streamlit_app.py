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
    REJECT_CODES,
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
st.subheader("verify your own chain")
st.caption(
    "the committed fixtures form one linear chain, but you only ever saw the "
    "happy path. here you drive the real chain engine (notary.verifier."
    "order_and_check) on receipts YOU edit. it topologically orders them "
    "root-first and rejects broken structure -- missing root, multiple roots, "
    "a dangling prior pointer, a fork, or a cycle. each surviving receipt is "
    "then re-verified with the real ed25519 verifier. mutate the JSON below and "
    "watch the verdict change live."
)

chain_default = "[\n" + ",\n".join(
    fixtures[k].read_text(encoding="utf-8").strip()
    for k in ("positive/minimal.json", "positive/chained-second.json", "positive/chained-third.json")
    if k in fixtures
) + "\n]"

with st.expander("what breaks a chain (try these edits)", expanded=False):
    st.markdown(
        "- delete the receipt whose `prior_receipt_id` is `null` -> "
        "`chain_no_root`\n"
        "- set two receipts' `prior_receipt_id` to the same value -> "
        "`chain_not_linear` (a fork)\n"
        "- point a receipt's `prior_receipt_id` at an id that is not in the "
        "list -> `chain_break`\n"
        "- make the receipts point at each other in a loop -> `cycle_detected`\n"
        "- flip a hex digit in any `action_canonical_hash` -> the structure "
        "still orders, but that receipt's `signature_invalid` shows up in the "
        "per-receipt column"
    )

chain_text = st.text_area(
    "receipts (a JSON array)",
    value=chain_default,
    height=360,
    key="chain_input",
)

if st.button("verify chain", type="primary", key="verify_chain_btn"):
    try:
        parsed = json.loads(chain_text)
    except json.JSONDecodeError as e:
        st.error(f"not valid JSON: {e}")
        st.stop()
    if not isinstance(parsed, list):
        st.error("expected a JSON array of receipt objects")
        st.stop()

    try:
        ordered = order_and_check(parsed)
    except VerifyError as e:
        st.error(f"chain REJECTED -- {e.code}: {e}")
        st.caption(f"reject code {e.code} (cli exit {REJECT_CODES.get(e.code, 1)})")
        st.stop()

    st.success(
        f"chain structure ACCEPTED -- {len(ordered)} receipts, root-first, "
        "no breaks, forks, or cycles."
    )
    rows = []
    all_sigs_ok = True
    for r in ordered:
        ok, reason = verify_one(r)
        if not ok:
            all_sigs_ok = False
        rid = str(r.get("receipt_id", ""))
        prior = r.get("prior_receipt_id")
        rows.append(
            {
                "order": len(rows) + 1,
                "receipt_id": rid[:14] + ("..." if len(rid) > 14 else ""),
                "prior": "(root)" if prior is None else str(prior)[:14] + "...",
                "sender": str(r.get("sender_identity", "")).rsplit("/", 1)[-1],
                "signature": "accept" if ok else f"reject: {reason}",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    if all_sigs_ok:
        st.info("every receipt also passed schema + ed25519 signature verification.")
    else:
        st.warning(
            "structure is sound, but at least one receipt failed signature "
            "verification (see the signature column)."
        )

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
