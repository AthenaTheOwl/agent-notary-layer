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

## Gates (will land in spec 0002)

```bash
uv run pytest
python scripts/voice_lint.py spec/ docs/
python scripts/validate_schemas.py
python scripts/check_conformance_coverage.py
```

A schema change without a corresponding RFC paragraph fails the
coverage gate. A verifier change without a conformance fixture also
fails.

## Out of scope

- Hosted verifier-as-a-service. Commercial concern; separate repo.
- Receipt revocation lists. Out of scope for v0; possible spec 0004.
- Confidential-compute attestation. Out of scope.
- Cryptocurrency settlement. The receipt format is settlement-agnostic.
