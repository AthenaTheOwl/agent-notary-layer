# Tasks — 0002 Design (v0.1)

Two PRs. PR-A lands the schema and single-receipt `verify`. PR-B lands
chain verification and the negative-fixture pytest pass.

## PR-A — schema + single-receipt verify

- [ ] Add `pyproject.toml` declaring `notary` console script
  → `verifier.cli:main`, Python 3.11+, pinned deps per
  design.md "External dependencies".
- [ ] Add `spec/agent-receipt.schema.json` per R-NOT-V1-002 and
  R-NOT-V1-003 with `additionalProperties: false` and
  `$id: https://notary.example/schema/agent-receipt/v0.1.json`.
- [ ] Add `spec/LICENSE.md` clarifying CC-BY-4.0 for the schema and
  MIT for the verifier code.
- [ ] Implement `verifier/schema_loader.py` exposing `load_schema()`
  and `validate(receipt)`.
- [ ] Implement `verifier/canon.py` with vendored RFC 8785 JCS plus
  `signed_bytes(receipt)` (omits the `signature` field).
- [ ] Implement `verifier/keys.py` `FileKeyResolver` reading
  `keys/<percent-encoded-did>.pub`.
- [ ] Implement `verifier/sig.py` `verify_ed25519` using `pynacl`.
- [ ] Implement `verifier/cli.py` with the `verify` subcommand and
  the exit-code table from design.md.
- [ ] Add `verifier/README.md` documenting the exit-code table and
  the `keys/` directory layout.
- [ ] Add `verifier/tests/test_verify.py` with one positive case and
  one negative case per reject code in R-NOT-V1-008 that the
  single-receipt path can produce.

## PR-B — chain verification

- [ ] Implement `verifier/chain.py` `order_and_check`.
- [ ] Add `verify-chain` subcommand to `verifier/cli.py`.
- [ ] Add `verifier/tests/test_chain.py` covering: linear three-receipt
  accept, two-root reject, missing-parent reject, cycle reject,
  no-root reject.
- [ ] Add a small fixture generator script under
  `verifier/tests/fixtures/_gen.py` that produces signed receipts
  from a checked-in ed25519 test keypair, so fixtures can be
  regenerated rather than checked in by hand.
- [ ] Add a CI workflow `.github/workflows/verify.yml` running
  `uv sync && uv run pytest`.

## Explicitly deferred

- [ ] RFC-001 prose.
- [ ] `spec/traceability.csv` and the traceability gate.
- [ ] `scripts/voice_lint.py`.
- [ ] The spec-0001 conformance directory layout
  (`verifier/tests/conformance/{positive,negative}/`).
- [ ] `make validate` aggregate.
- [ ] Any non-file key resolver.
