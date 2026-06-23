# Notary Layer

Tamper-evident, receiver-attested receipt schema for every
cross-organization agent action: PO commit, payment authorization,
contract redline acceptance. Shipped as a JSON Schema spec plus a
reference verifier CLI plus a conformance suite. The audit trail
Agent2Agent and Stripe MPP defined no schema for.

## What this is

A schema-first repo. Three primary artifacts:

1. `spec/agent-receipt.schema.json` — the receipt format itself.
2. `src/notary/` — a reference verifier (`notary` CLI) that checks
   receipts against the schema and replays ed25519 signatures.
3. `conformance/` — the conformance fixtures (positive + negative) that
   any third-party verifier must reproduce to claim spec compliance.

The receipt is a small JSON object: receiver identity, sender identity,
action canonical hash, prior-receipt hash (for chaining), timestamp,
signature. The format is designed to survive a regulator's adversarial
replay without leaking the underlying business payload.

## Status

v0.1, implemented and tested. The schema (`spec/agent-receipt.schema.json`),
the RFC 8785 canonicalizer (`src/notary/canonical.py`), the verifier
(`src/notary/verifier.py`), and the CLI (`src/notary/cli.py`) are real and
covered by `tests/`. The Pactum-style worked example under `examples/` is
still pending.

## How to run

```bash
uv sync
# verify a single receipt against the committed demo keys
uv run notary verify conformance/positive/minimal.json --keys-dir keys
# verify a directory of receipts forming one linear chain
uv run notary verify-chain conformance/positive --keys-dir keys
# no-arg demo: verify every bundled conformance receipt and report
uv run notary show
```

Equivalently, `python -m notary <subcommand>` works (the package ships a
`__main__`). Run `uv run notary --help` for the full subcommand list:
`verify`, `verify-chain`, `show` (alias `demo`).

`notary verify` resolves the signer's public key from `--keys-dir` (default
`./keys`): one file per identity, named with the percent-encoded identity
plus `.pub`, holding base64 of the 32-byte ed25519 public key. The committed
`keys/` directory holds the synthetic demo keys for the conformance fixtures
(not secret).

There is no separate `conformance` subcommand: the conformance suite is just
the fixtures under `conformance/`, which `notary show` walks (positives must
accept, negatives must reject) and which `tests/test_conformance.py` runs
through the verifier.

## Tests

```bash
uv run pytest -q
```

## Live demo

A Streamlit app (`streamlit_app.py`) wraps the reference verifier: pick a
committed conformance receipt or paste your own, verify it (schema + signer
resolution + ed25519 signature), and see the linear chain plus a live tamper
check (flipping one hex digit of the action hash breaks the signature). It
defaults to the committed conformance receipts and runs entirely off
committed fixtures and demo keys — no network, no secrets.

Run locally:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Deploy on Streamlit Community Cloud: New app -> this repo, branch `main`,
main file `streamlit_app.py`. `requirements.txt` pulls `streamlit` plus the
verifier's runtime deps (`jsonschema`, `PyNaCl`).

## Layout

```
agent-notary-layer/
  spec/
    agent-receipt.schema.json   # the receipt JSON Schema (v0.1)
    RFC-001-receipt-format.md   # the human-readable RFC
  src/notary/
    canonical.py                # RFC 8785 JCS canonicalizer
    verifier.py                 # schema + key + signature + chain checks
    cli.py                      # verify / verify-chain / show
    __main__.py                 # enables `python -m notary`
  conformance/
    positive/                   # fixtures that must accept
    negative/                   # fixtures that must reject
  keys/                         # synthetic demo public keys for the fixtures
  tests/                        # unit + end-to-end conformance tests
  streamlit_app.py              # live demo (Streamlit Community Cloud)
  requirements.txt              # demo deps
  examples/
    pactum_replay/              # worked example (pending)
  specs/                        # design specs
  docs/first-pr.md
  AGENTS.md
  LICENSE
  README.md
```

## License

MIT for the verifier code (see `LICENSE`). The schema and the RFC are
intended as CC-BY-4.0; a dedicated `spec/LICENSE.md` recording that split
is still pending.

## Distribution intent

The spec is intended for submission to the A2A working group and the
NIST AI RMF public-comment window. The hosted verifier service is a
separate, commercial concern outside this repo.
