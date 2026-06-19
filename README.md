# Notary Layer

Tamper-evident, receiver-attested receipt schema for every
cross-organization agent action: PO commit, payment authorization,
contract redline acceptance. Shipped as a JSON Schema spec plus a
reference verifier CLI plus a conformance suite. The audit trail
Agent2Agent and Stripe MPP defined no schema for.

## What this is

A schema-first repo. Three primary artifacts:

1. `spec/agent-receipt.schema.json` — the receipt format itself.
2. `verifier/cli.py` — a reference verifier that checks receipts
   against the schema and replays signatures.
3. `verifier/tests/conformance/` — the conformance suite that any
   third-party verifier must pass to claim spec compliance.

The receipt is a small JSON object: receiver identity, sender identity,
action canonical hash, prior-receipt hash (for chaining), timestamp,
signature. The format is designed to survive a regulator's adversarial
replay without leaking the underlying business payload.

## Status

v0 scaffold; no implementation yet. Spec 0002 will land the schema and
verifier CLI. Spec 0003 will land the Pactum-style worked example.

## How to run

Will land in spec 0002. The expected shape:

```bash
uv sync
uv run notary verify path/to/receipt.json
uv run notary verify-chain path/to/receipts/
uv run notary conformance --suite verifier/tests/conformance/
```

For v0 the only working command is `uv run notary --help`.

## Layout

```
agent-notary-layer/
  spec/
    agent-receipt.schema.json   # the schema (lands in spec 0002)
    RFC-001-receipt-format.md   # the human-readable RFC
  verifier/
    cli.py                      # reference verifier (spec 0002)
    tests/conformance/          # conformance fixtures (spec 0002)
  examples/
    pactum_replay/              # worked example (spec 0003)
  specs/0001-foundation/
  docs/first-pr.md
  AGENTS.md
  LICENSE
  README.md
```

## License

MIT for the verifier code. The schema and the RFC are CC-BY-4.0; that
distinction is in `spec/LICENSE.md` (lands in spec 0002).

## Distribution intent

The spec is intended for submission to the A2A working group and the
NIST AI RMF public-comment window. The hosted verifier service is a
separate, commercial concern outside this repo.
