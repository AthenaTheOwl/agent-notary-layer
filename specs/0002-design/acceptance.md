# Acceptance — 0002 Design (v0.1)

## What v0.1 done means

A stranger clones the repo, runs the commands below on a clean
machine with Python 3.11+ and `uv` installed, and every command exits
0 with the stated output.

## Commands to run on a fresh clone

```bash
git clone <repo>
cd agent-notary-layer-task-batch2-agent-notary-layer-design
uv sync
uv run pytest
uv run notary --help
uv run notary verify verifier/tests/fixtures/positive/minimal.json
uv run notary verify-chain verifier/tests/fixtures/positive/chain-three/
```

## Expected outcomes

- `uv sync` resolves with no network errors; `uv.lock` is committed.
- `uv run pytest` ends with `passed` and zero `failed` / `errored`.
  The suite includes at least one test per reject code in
  R-NOT-V1-008.
- `uv run notary --help` prints both subcommands (`verify`,
  `verify-chain`) and exits 0.
- `uv run notary verify verifier/tests/fixtures/positive/minimal.json`
  prints `accept` to stdout and exits 0.
- `uv run notary verify-chain verifier/tests/fixtures/positive/chain-three/`
  prints `accept (3 receipts)` to stdout and exits 0.

## Negative-path spot checks

```bash
uv run notary verify verifier/tests/fixtures/negative/missing-signature.json
# stderr: reject: schema_invalid; exit 2

uv run notary verify verifier/tests/fixtures/negative/tampered-hash.json
# stderr: reject: signature_invalid; exit 5

uv run notary verify-chain verifier/tests/fixtures/negative/two-roots/
# stderr: reject: chain_not_linear; exit 6

uv run notary verify-chain verifier/tests/fixtures/negative/missing-parent/
# stderr: reject: chain_break; exit 7
```

Each command's exit code SHALL match the table in `verifier/README.md`.

## Schema spot check

```bash
uv run python -c "import json, jsonschema; \
  s=json.load(open('spec/agent-receipt.schema.json')); \
  jsonschema.Draft202012Validator.check_schema(s); print('schema ok')"
```

Expected: `schema ok`.

## Out of scope for v0.1 acceptance

- `make validate` aggregate gate (spec 0003).
- Voice-lint pass on RFC prose (no RFC yet).
- Traceability CSV gate (spec 0003).
- Conformance directory layout matching spec 0001's design (spec 0003
  will move fixtures from `verifier/tests/fixtures/` into the
  `conformance/{positive,negative}/<name>/expected.txt` shape).
- Third-party verifier compatibility (downstream).
