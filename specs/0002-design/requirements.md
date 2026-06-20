# Requirements — 0002 Design (v0.1)

Narrowed scope from spec 0001. v0.1 ships two artifacts: a JSON Schema
for agent receipts and a reference verifier CLI with two commands
(`verify`, `verify-chain`). RFC prose, the full conformance suite, the
traceability gate, voice-lint, and schema-version churn machinery defer
to spec 0003.

Carry-overs from spec 0001 are noted in parentheses.

## Functional requirements

- **R-NOT-V1-001** The repo SHALL ship `spec/agent-receipt.schema.json`
  written against JSON Schema draft 2020-12 with a stable `$id` of
  `https://notary.example/schema/agent-receipt/v0.1.json`.
  (refines R-NOT-001)

- **R-NOT-V1-002** Each receipt object SHALL include exactly these
  required fields: `receipt_id`, `prior_receipt_id` (nullable string),
  `action_canonical_hash`, `sender_identity`, `receiver_identity`,
  `timestamp`, `signature`, `signature_algorithm`. Additional
  properties SHALL be rejected by the schema.
  (refines R-NOT-002)

- **R-NOT-V1-003** The schema SHALL constrain field shapes:
  `receipt_id` and `prior_receipt_id` to ULID (Crockford base32, 26
  chars); `action_canonical_hash` to the literal regex
  `^sha256:[0-9a-f]{64}$`; `timestamp` to RFC 3339 with a `Z` suffix;
  `signature` to base64 of 64 bytes; `signature_algorithm` to the enum
  `["ed25519"]`.

- **R-NOT-V1-004** The schema SHALL NOT permit any field that could
  carry the business payload (no `payload`, no `body`, no `data`, no
  `attachments`). Only the canonical hash is in band.
  (refines R-NOT-003)

- **R-NOT-V1-005** The repo SHALL ship a `pyproject.toml` declaring a
  `notary` console script that resolves to `verifier.cli:main`. Python
  3.11+.

- **R-NOT-V1-006** `notary verify <path>` SHALL: parse the file as JSON,
  validate against the schema, resolve `sender_identity` via the
  file-backed key resolver, recompute the signed bytes (the receipt
  serialized via RFC 8785 JCS with the `signature` field omitted), and
  verify the ed25519 signature. Exit 0 on accept; nonzero with a typed
  error code on reject.
  (refines R-NOT-005)

- **R-NOT-V1-007** `notary verify-chain <dir>` SHALL: load every `.json`
  file in the directory (non-recursive), topologically sort by
  `prior_receipt_id`, reject if the result is not a single linear
  chain rooted at a receipt with `prior_receipt_id: null`, run the
  single-receipt verify on each, and confirm each non-root receipt's
  `prior_receipt_id` equals its predecessor's `receipt_id`.

- **R-NOT-V1-008** The verifier SHALL expose a fixed set of typed
  reject codes: `schema_invalid`, `bad_canonical_hash_format`,
  `unknown_signer`, `signature_invalid`, `chain_not_linear`,
  `chain_break`, `chain_no_root`, `cycle_detected`. Each maps to a
  distinct nonzero exit code documented in `verifier/README.md`.

- **R-NOT-V1-009** The file-backed key resolver SHALL read public keys
  from `keys/<sender_identity-percent-encoded>.pub`, where the file
  body is a base64-encoded 32-byte ed25519 public key. Missing file
  SHALL produce `unknown_signer`.

## Non-functional requirements

- **R-NOT-V1-010** Verifier code SHALL be MIT-licensed; the schema
  SHALL ship under CC-BY-4.0 inside `spec/LICENSE.md`.
  (carries R-NOT-008)

- **R-NOT-V1-011** The verifier SHALL run on a clean clone with
  `uv sync && uv run pytest` passing. Test dependencies (`pytest`,
  `jsonschema`, `pynacl`, `ulid-py`) SHALL be pinned in
  `pyproject.toml` with upper-bound minor versions.

- **R-NOT-V1-012** Every reject code in R-NOT-V1-008 SHALL have at
  least one pytest case asserting the verifier emits that code on a
  crafted negative fixture under `verifier/tests/fixtures/`. The full
  conformance suite per R-NOT-006 is deferred to spec 0003.
