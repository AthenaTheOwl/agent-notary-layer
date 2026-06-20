# RFC-001 — agent-receipt format (v0.1 excerpt)

Status: draft. This is the v0.1 excerpt that ships alongside the schema
and the reference verifier. The full prose RFC (motivation, threat
model, alternatives considered, security considerations) lands in spec
0003.

## 1. Receipt object

A receipt is a single JSON object with exactly the eight fields below,
no more, no less. The schema in `spec/agent-receipt.schema.json` is
normative; this section restates the field semantics for human readers.

| field                    | type           | normative shape                                                |
|--------------------------|----------------|----------------------------------------------------------------|
| `receipt_id`             | string         | ULID, Crockford base32, 26 chars.                              |
| `prior_receipt_id`       | string or null | ULID of the immediate predecessor, or `null` at the chain root.|
| `action_canonical_hash`  | string         | `sha256:` + 64 lowercase hex chars over the JCS form of the    |
|                          |                | underlying business action object.                             |
| `sender_identity`        | string         | Opaque signer identifier (typically a DID). Non-empty.         |
| `receiver_identity`      | string         | Opaque counterparty identifier. Non-empty.                     |
| `timestamp`              | string         | RFC 3339, UTC, trailing `Z`.                                   |
| `signature`              | string         | Base64 of the 64-byte ed25519 signature.                       |
| `signature_algorithm`    | string         | Literal `"ed25519"`.                                           |

The business action object itself is NOT part of the receipt. The chain
proves consent without exposing payload.

## 2. Canonicalization (signed bytes)

The signed bytes are the receipt object with the `signature` field
omitted, serialized via RFC 8785 JSON Canonicalization Scheme:

- Object members sorted lexicographically by key (UTF-16 code units).
- No insignificant whitespace.
- Strings escape only `"`, `\`, and control characters U+0000–U+001F.
- Numbers serialize per ES6 `ToString(Number)`.

The verifier MUST recompute these bytes from the parsed receipt rather
than treating the wire bytes as canonical. Two byte sequences that
serialize the same object MUST verify identically.

## 3. Signing

`signature_algorithm` MUST be `"ed25519"` in v0.1. The signature is
base64 of the 64-byte raw ed25519 signature over the bytes from §2,
under the public key associated with `sender_identity`.

Key resolution is out of band. The reference verifier ships one
resolver: a file-backed resolver that reads
`keys/<percent-encoded-sender_identity>.pub` containing the base64 of a
32-byte ed25519 public key. Pluggable resolvers (DID web, KMS) are
deferred to spec 0003.

## 4. Chaining

A receipt with `prior_receipt_id: null` is a chain root. Any other
receipt MUST name a predecessor whose `receipt_id` equals the
successor's `prior_receipt_id`. A chain is a linear sequence of
receipts: exactly one root, each non-root has exactly one predecessor,
no cycles, no forks.

## 5. Verifier reject codes

The reference verifier's typed reject codes are part of the spec
contract:

| code                       | meaning                                          |
|----------------------------|--------------------------------------------------|
| `schema_invalid`           | object fails the JSON Schema.                    |
| `bad_canonical_hash_format`| `action_canonical_hash` fails its regex after    |
|                            | all other schema rules pass.                     |
| `unknown_signer`           | no public key for `sender_identity`.             |
| `signature_invalid`        | ed25519 verify fails or signature is malformed.  |
| `chain_no_root`            | no receipt has `prior_receipt_id: null`.         |
| `chain_not_linear`         | more than one root, or a fork.                   |
| `chain_break`              | a non-root names a predecessor not in the input. |
| `cycle_detected`           | following predecessors revisits a receipt.       |

The exit-code mapping is documented in `pyproject.toml`'s console
script (`notary`) help and in this RFC's machine-readable companion in
spec 0003.

## 6. Deferred to spec 0003+

- Threat model and security considerations prose.
- Pluggable key resolvers (DID web, KMS).
- Receipt revocation.
- Additional signature algorithms.
- The traceability matrix tying each MUST in §1–§5 to a schema rule and
  a conformance fixture.
