# Design — 0002 Design (v0.1)

## Scope reminder

v0.1 ships the schema file and a CLI that verifies one receipt or a
directory of receipts forming a chain. Everything else from spec 0001
(RFC prose, traceability matrix, full conformance suite, voice-lint,
schema-version migration tooling) defers.

## Block decomposition

```
+------------------+         +---------------------+
| spec/            |         | verifier/           |
| agent-receipt    |  read   |                     |
| .schema.json (A) | <-----  | schema_loader (B)   |
+------------------+         +---------+-----------+
                                       |
                                       v
                             +---------+-----------+
                             | canon (C)           |
                             | JCS + signed-bytes  |
                             +---------+-----------+
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
       +--------+---------+                          +--------+--------+
       | keys (D)         |                          | sig (E)         |
       | file resolver    |                          | ed25519 verify  |
       +--------+---------+                          +--------+--------+
                |                                             |
                +----------------------+----------------------+
                                       v
                             +---------+-----------+
                             | chain (F)           |
                             | topo-sort + link    |
                             | check               |
                             +---------+-----------+
                                       |
                                       v
                             +---------+-----------+
                             | cli (G)             |
                             | verify, verify-chain|
                             +---------------------+
```

Dependency edges run only downward. No cycles.

### A. `spec/agent-receipt.schema.json`

JSON Schema draft 2020-12. The artifact, not code. Constraints land per
R-NOT-V1-002 and R-NOT-V1-003. `additionalProperties: false`.

### B. `verifier/schema_loader.py`

```python
def load_schema() -> dict: ...
def validate(receipt: dict) -> None  # raises SchemaInvalid
```

Reads the schema from a packaged resource path. Uses `jsonschema`
library's `Draft202012Validator`.

Failure modes:
- File missing on disk → packaging error; `SchemaLoadError`.
- Receipt fails any schema rule → `SchemaInvalid(path, rule)`.

### C. `verifier/canon.py`

```python
def signed_bytes(receipt: dict) -> bytes
```

Returns the RFC 8785 JCS canonicalization of the receipt with the
`signature` field removed. Uses a vendored 80-line JCS implementation
(no external `jcs` package — see "External dependencies" below).

Failure modes:
- Receipt contains a non-JSON-serializable value → `CanonError`. The
  caller is expected to have run schema validation first, so this
  should be unreachable; if hit, exit code is internal-error.

### D. `verifier/keys.py`

```python
class FileKeyResolver:
    def __init__(self, root: pathlib.Path): ...
    def resolve(self, sender_identity: str) -> bytes  # 32-byte pubkey
```

Maps `sender_identity` to a file path by percent-encoding the identity
string and appending `.pub`. Reads base64. Returns raw 32 bytes.

Failure modes:
- File missing → `UnknownSigner(sender_identity)`.
- File contains non-base64 or wrong byte length → `KeyMalformed`.

### E. `verifier/sig.py`

```python
def verify_ed25519(pubkey: bytes, message: bytes, sig_b64: str) -> None
```

Wraps `pynacl`'s `nacl.signing.VerifyKey`. Decodes the base64 signature
and calls `verify`. Raises `SignatureInvalid` on mismatch.

Failure modes:
- `signature` field is not valid base64 → `SignatureInvalid`.
- Decoded signature is not 64 bytes → `SignatureInvalid`.
- `pubkey` is the wrong length → `KeyMalformed` (re-raised from D).

### F. `verifier/chain.py`

```python
def order_and_check(receipts: list[dict]) -> list[dict]
```

Input is the unordered list parsed from a directory. Output is the
list ordered root-first. The function:
1. Builds a map `receipt_id -> receipt`.
2. Finds receipts with `prior_receipt_id is None`. Exactly one
   required → otherwise `ChainNoRoot` or `ChainNotLinear`.
3. Walks forward following `prior_receipt_id` links of the children,
   detecting cycles (`CycleDetected`) and breaks (`ChainBreak`).
4. Returns the linear list.

Single-receipt `verify` skips F.

Failure modes:
- Zero or multiple roots → `ChainNoRoot` / `ChainNotLinear`.
- Forward walk visits a receipt twice → `CycleDetected`.
- A child names a `prior_receipt_id` not in the directory →
  `ChainBreak`.
- Any receipt fails its own `verify` step → that receipt's error
  bubbles unchanged.

### G. `verifier/cli.py`

`argparse` (stdlib, no Click) front-end. Two subcommands:

```
notary verify <path-to-receipt.json> [--keys-dir DIR]
notary verify-chain <dir-of-receipts> [--keys-dir DIR]
```

`--keys-dir` defaults to `./keys`. Exit code table:

| code | reject reason            |
|------|--------------------------|
| 0    | accept                   |
| 2    | schema_invalid           |
| 3    | bad_canonical_hash_format|
| 4    | unknown_signer           |
| 5    | signature_invalid        |
| 6    | chain_not_linear         |
| 7    | chain_break              |
| 8    | chain_no_root            |
| 9    | cycle_detected           |
| 10   | key_malformed (internal) |

`bad_canonical_hash_format` overlaps `schema_invalid` at the schema
layer; it is a distinct reject code only when the regex fires after
all other schema rules pass — kept distinct so callers can route the
two cases differently.

## Interface contracts

| consumer        | provider        | shape                                     |
|-----------------|-----------------|-------------------------------------------|
| cli             | schema_loader   | `validate(dict) -> None or raises`        |
| cli             | canon           | `signed_bytes(dict) -> bytes`             |
| cli             | keys            | `resolve(str) -> 32-byte bytes`           |
| cli             | sig             | `verify_ed25519(bytes, bytes, str)`       |
| cli             | chain           | `order_and_check(list[dict]) -> list[dict]` |
| schema_loader   | filesystem      | packaged resource at `spec/...schema.json`|
| keys            | filesystem      | `keys/<percent-encoded-did>.pub`          |

All raised exceptions are subclasses of `VerifyError`, each carrying
the reject code from R-NOT-V1-008.

## External dependencies

| dep         | purpose                            | license | failure mode                |
|-------------|------------------------------------|---------|-----------------------------|
| `jsonschema`| Draft 2020-12 validator            | MIT     | API churn — pinned `>=4.21,<5` |
| `pynacl`    | ed25519 verify                     | Apache-2| ABI on Windows — wheels exist |
| `pytest`    | tests                              | MIT     | dev-only; pinned `>=8,<9`   |
| `ulid-py`   | only in test fixtures, never runtime | MIT  | dev-only                    |

No `jcs` package. The Python ecosystem JCS libraries are abandoned;
vendoring the canonicalizer (~80 lines, deterministic JSON sort +
escape rules per RFC 8785) is the better risk profile than depending
on a stale package. Code lives in `verifier/canon.py` with the RFC
section numbers in a header comment.

No network calls. No DID resolution. The key resolver is filesystem
only.

## Failure-mode summary (cross-block)

| input failure              | detected by | reject code              |
|----------------------------|-------------|--------------------------|
| not JSON                   | cli         | schema_invalid           |
| missing required field     | schema      | schema_invalid           |
| extra field                | schema      | schema_invalid           |
| bad ULID shape             | schema      | schema_invalid           |
| bad hash regex             | schema      | bad_canonical_hash_format|
| key file absent            | keys        | unknown_signer           |
| key file wrong length      | keys        | key_malformed            |
| signature decode failure   | sig         | signature_invalid        |
| signature does not verify  | sig         | signature_invalid        |
| chain has two roots        | chain       | chain_not_linear         |
| chain has no root          | chain       | chain_no_root            |
| child names missing parent | chain       | chain_break              |
| chain has cycle            | chain       | cycle_detected           |

## Out of scope for v0.1

- RFC-001 prose (`spec/RFC-001-receipt-format.md`).
- `spec/traceability.csv` and `scripts/check_traceability.py`.
- `scripts/voice_lint.py`.
- Conformance suite layout per R-NOT-006 (positive/negative
  directories with `expected.txt` siblings). v0.1 ships pytest
  fixtures only.
- `make validate` aggregate gate.
- Pluggable key resolvers (DID web, KMS).
- Receipt revocation lists.
- Pactum-style worked example (spec 0004).
- Signature algorithms beyond ed25519.
- Schema-version migration tooling and the second `$id` URL.
- Hosted verifier service.
