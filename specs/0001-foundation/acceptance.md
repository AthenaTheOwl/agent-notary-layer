# Acceptance — 0001 Foundation

## What v0 done means

- `spec/RFC-001-receipt-format.md` is readable end-to-end and every
  MUST clause has a schema constraint and a negative fixture.
- `spec/agent-receipt.schema.json` validates with a stock JSON Schema
  validator.
- `notary verify` accepts every positive fixture and rejects every
  negative fixture with the correct error code.
- `notary verify-chain` accepts the three-receipt chained fixture and
  rejects the broken-chain fixture.
- `make validate` passes on a clean clone.

## Commands to run

```bash
git clone <repo>
cd agent-notary-layer
uv sync
make validate
uv run notary verify verifier/tests/conformance/positive/minimal-valid.json
uv run notary verify-chain verifier/tests/conformance/positive/chained-three.json/
```

Expected: zero exit codes for both verify calls; `make validate` ends
with `OK: traceability complete, conformance coverage complete.`

## Gates to pass

- `python scripts/voice_lint.py spec/ docs/` — no banned terms.
- `python scripts/validate_schemas.py` — schema parses.
- `python scripts/check_traceability.py` — every RFC normative claim
  references at least one schema constraint and one fixture.
- `python scripts/check_conformance_coverage.py` — every MUST has at
  least one negative fixture.
- `uv run pytest` — verifier verdicts match fixture expectations.

## Out of scope for acceptance

- Pluggable key resolvers (spec 0003).
- Pactum-style worked example (spec 0003).
- Third-party verifier conformance verification (downstream concern).
