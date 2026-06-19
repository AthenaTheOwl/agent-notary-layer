# Tasks — 0001 Foundation

## PR 1 — RFC skeleton + schema stub

- [ ] Draft `spec/RFC-001-receipt-format.md` with sections: Abstract,
  Motivation, Terminology, Receipt Format, Signature Algorithm,
  Chaining, Conformance.
- [ ] Add `spec/agent-receipt.schema.json` stub with required fields
  per R-NOT-002.
- [ ] Add `spec/LICENSE.md` clarifying CC-BY-4.0 for spec, MIT for code.
- [ ] Add `spec/traceability.csv` with header row.
- [ ] Add `scripts/voice_lint.py` copied from sports-prediction-os.
- [ ] Add `scripts/validate_schemas.py`.
- [ ] Add `Makefile` with `validate` target.

## PR 2 — Reference verifier MVP

- [ ] Add `pyproject.toml` with `notary` console script.
- [ ] Implement `notary verify` for a single receipt against a
  file-backed key resolver.
- [ ] Add five positive and five negative fixtures under
  `verifier/tests/conformance/`.
- [ ] Add pytest cases asserting reference-verifier verdicts match
  `expected.txt`.
- [ ] Update `spec/traceability.csv` to cover every fixture.

## PR 3 — Chain verification + traceability gate

- [ ] Implement `notary verify-chain`.
- [ ] Add a three-receipt chained fixture.
- [ ] Add `scripts/check_traceability.py` enforcing R-NOT-011.
- [ ] Wire `make validate` to also run traceability.
- [ ] Add `scripts/check_conformance_coverage.py` confirming every
  normative MUST in the RFC has at least one negative fixture.

## Out of scope for foundation

- [ ] Pactum-style worked example (spec 0003).
- [ ] Receipt revocation lists.
- [ ] Pluggable key resolvers beyond the file-backed one.
