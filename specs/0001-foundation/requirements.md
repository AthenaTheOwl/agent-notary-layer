# Requirements — 0001 Foundation

## Functional requirements

- **R-NOT-001** The repo SHALL maintain a JSON Schema document at
  `spec/agent-receipt.schema.json`.
- **R-NOT-002** Each receipt object SHALL include: `receipt_id`,
  `prior_receipt_id` (nullable), `action_canonical_hash`,
  `sender_identity`, `receiver_identity`, `timestamp` (RFC 3339 UTC),
  `signature` (base64), `signature_algorithm`.
- **R-NOT-003** The schema SHALL forbid the business payload from
  appearing in the receipt; only its canonical hash is permitted.
- **R-NOT-004** The repo SHALL ship a human-readable RFC at
  `spec/RFC-001-receipt-format.md` whose normative claims correspond
  one-to-one with schema constraints.
- **R-NOT-005** The repo SHALL ship a reference verifier CLI exposing
  `verify` (single receipt) and `verify-chain` (a directory of receipts
  ordered by `prior_receipt_id`).
- **R-NOT-006** The conformance suite SHALL include positive fixtures
  (valid receipts that MUST pass) and negative fixtures (invalid
  receipts that MUST fail) covering each normative claim.
- **R-NOT-007** A third-party verifier passes conformance iff it
  produces the same accept / reject verdict as the reference verifier
  on every fixture.

## Non-functional requirements

- **R-NOT-008** Schema and RFC SHALL be released under CC-BY-4.0;
  verifier code under MIT.
- **R-NOT-009** All prose SHALL pass `scripts/voice_lint.py`.
- **R-NOT-010** Schema changes SHALL bump the schema's `$id` URL
  version path and add a CHANGELOG entry; old versions remain
  resolvable.
- **R-NOT-011** Every normative claim in the RFC SHALL be traceable to
  at least one schema constraint and at least one conformance fixture.
