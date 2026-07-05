# AGENTS.md — agent-notary-layer

Operating contract for AI agents working in this repo.

## What this repo is

A schema and a reference verifier for tamper-evident receipts on
cross-organization agent actions. The schema is the contract; the
verifier is the proof the schema is implementable; the conformance suite
is the test any third-party verifier must pass.

The repo is intended to be read by standards-body reviewers. Voice,
schema clarity, and conformance fidelity matter more than feature
breadth.

## Roles you may see in tasks

| Role | What they do |
|---|---|
| `schema-author` | Drafts and revises `spec/agent-receipt.schema.json` |
| `rfc-writer` | Maintains the human-readable RFC alongside the schema |
| `verifier-implementer` | Writes the reference verifier in lockstep with the schema |
| `conformance-curator` | Adds positive and negative test fixtures |

Not all roles are implemented in v0.

## Voice constraints

- No marketing words. No "leverage", "synergy", "best-in-class",
  "seamless", "cutting-edge".
- No antithetical reversals as a structural device.
- RFC prose follows IETF style: "MUST", "SHOULD", "MAY" in caps; one
  normative claim per paragraph.

## Gates

The runnable gate today is:

```bash
uv run pytest
```

The following gate scripts are planned but unbuilt. They MUST NOT be
listed as runnable commands until the scripts exist in this repo.

- `scripts/voice_lint.py` was named in spec 0001 and is explicitly
  deferred by `specs/0002-design/tasks.md`.
- `scripts/validate_schemas.py` was named in spec 0001 and is currently
  unscheduled after spec 0002.
- `scripts/check_conformance_coverage.py` was named in spec 0001 and is
  currently unscheduled after spec 0002.

When implemented, a schema change without a corresponding RFC paragraph
will fail the coverage gate. A verifier change without a conformance
fixture will fail the conformance gate.

## Out of scope

- Hosted verifier-as-a-service. Commercial concern; separate repo.
- Receipt revocation lists. Out of scope for v0; possible spec 0004.
- Confidential-compute attestation. Out of scope.
- Cryptocurrency settlement. The receipt format is settlement-agnostic.
