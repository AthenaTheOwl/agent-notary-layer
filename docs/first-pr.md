# First PR after the scaffold

Narrow scope: RFC skeleton, schema stub, license clarification,
traceability CSV, voice + schema validators. No verifier code yet.

## Title

`feat: RFC-001 skeleton, receipt schema stub, traceability matrix`

## Files changed

- `spec/RFC-001-receipt-format.md` (new) — sections per the design doc:
  Abstract, Motivation, Terminology, Receipt Format, Signature
  Algorithm, Chaining, Conformance. Normative claims tagged with stable
  IDs (e.g. `MUST-001`).
- `spec/agent-receipt.schema.json` (new) — JSON Schema draft 2020-12,
  required fields per R-NOT-002, additionalProperties false.
- `spec/LICENSE.md` (new) — CC-BY-4.0 for the schema and RFC; MIT (per
  root LICENSE) for the verifier code.
- `spec/traceability.csv` (new) — header row `must_id,schema_path,fixture_id`;
  one initial row per MUST claim with `fixture_id` blank (to be filled in
  PR 2).
- `scripts/voice_lint.py` (new) — copied from sports-prediction-os.
- `scripts/validate_schemas.py` (new) — parses every `*.schema.json`
  under `spec/` with `jsonschema.Draft202012Validator.check_schema`.
- `Makefile` (new) — `make validate` runs both scripts.

## Verification

```bash
make validate
```

Expected output:
```
voice_lint: OK
validate_schemas: OK (1 schema)
```

A reviewer should read the RFC end-to-end and confirm every MUST
clause is needed to make the receipt format unambiguous. RFC bloat is
the failure mode here.

## What this PR does NOT do

- No verifier implementation; PR 2.
- No conformance fixtures; PR 2.
- No traceability gate enforcement; PR 3.
- No GitHub Action.
