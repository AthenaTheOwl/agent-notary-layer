# Design — 0001 Foundation

## Architecture sketch

Three artifacts, one repo, one canonical compatibility matrix.

```
+-----------------------+      +------------------+      +--------------------+
| RFC-001 (prose, MUST) | <--> | schema.json      | <--> | conformance suite  |
| normative claims      |      | constraints      |      | positive/negative  |
+-----------------------+      +------------------+      +--------------------+
                                       ^
                                       |
                             +---------+---------+
                             | verifier CLI      |
                             | (reference impl)  |
                             +-------------------+
```

The compatibility matrix is `spec/traceability.csv`: rows are normative
RFC claims, columns are schema constraints and fixture IDs. Each cell
is 1 or 0. `scripts/check_traceability.py` fails if any row has zero
columns.

## Receipt format (sketch)

```json
{
  "receipt_id": "01J7Z9PM4N2X3F0K0F0A0J3T1Y",
  "prior_receipt_id": "01J7Z9PM4M0K3F0K0F0A0J3T1Y",
  "action_canonical_hash": "sha256:7c1e...",
  "sender_identity": "did:web:pactum.example/agents/buyer-1",
  "receiver_identity": "did:web:supplier.example/agents/quoter-3",
  "timestamp": "2026-07-04T14:22:31Z",
  "signature": "MEUCIQ...==",
  "signature_algorithm": "ed25519"
}
```

The `action_canonical_hash` is the SHA-256 over the
JSON-Canonicalization-Scheme (RFC 8785) form of the underlying business
action object. The business object itself is held out-of-band by the
parties; the chain proves consent without exposing payload.

## Verifier behavior

`notary verify path/to/receipt.json`:
1. Parse JSON.
2. Validate against `spec/agent-receipt.schema.json`.
3. Resolve `sender_identity` to a public key (the resolution layer is
   pluggable; v0 ships a file-backed resolver for testing).
4. Verify the signature over the canonical receipt minus the
   `signature` field.
5. Exit 0 on accept; nonzero with a typed error on reject.

`notary verify-chain path/to/receipts/`:
1. Topo-sort by `prior_receipt_id`.
2. Run `verify` on each.
3. Confirm each `prior_receipt_id` matches the chained predecessor's
   `receipt_id`.
4. Reject on any break.

## Conformance directory shape

```
verifier/tests/conformance/
  positive/
    minimal-valid.json
    chained-three.json/
      001.json
      002.json
      003.json
  negative/
    missing-signature.json
    tampered-payload-hash.json
    broken-chain/
      001.json
      002.json
```

Each subdirectory has a sibling `expected.txt` with the expected
verdict (`accept` or `reject:<error_code>`).
