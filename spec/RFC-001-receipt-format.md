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

## 4a. Delegated hops (v0.2)

A receipt MAY carry an `authorization` object, `{authorizing_receipt_id,
delegator_identity}`, when the sender acts on authority another party
granted it. The object is part of the signed bytes. When verifying a
bundle, the authorizing receipt MUST be present and earlier in the chain,
MUST have been issued by `delegator_identity`, and MUST have been issued
to this receipt's `sender_identity`. Receipts without `authorization`
verify exactly as in v0.1.

## 4b. Usage actions (v0.3)

A usage action records one use of a payee's content. It is a JSON object
with exactly the four fields below. The receipt gains no fields: the
action travels beside the receipt, and the receipt's
`action_canonical_hash` MUST be `sha256:` + the SHA-256 of the action's
JCS form (§2).

| field            | type   | normative shape                                              |
|------------------|--------|--------------------------------------------------------------|
| `kind`           | string | Literal `"usage"`.                                           |
| `passage_sha256` | string | 64 lowercase hex chars: SHA-256 of the passage's UTF-8 bytes.|
| `answer_id`      | string | Payer's identifier for the answer that used the passage.     |
|                  |        | Non-empty.                                                   |
| `source_id`      | string | Identifier for the payee source the passage came from.       |
|                  |        | Non-empty.                                                   |

Payer and payee MUST split content into passages by one rule. The text is
decoded as UTF-8, a leading byte-order mark is dropped, and CRLF and CR
become LF. A blank line is empty or holds only spaces and tabs. A passage
is a maximal run of non-blank lines, kept as written and joined with LF.

A different split produces different hashes and rejects honest uses. A
payer that quotes part of a passage MUST still hash the whole passage it
came from.

When checking a billing period, a verifier MUST first verify the bundle
as a chain under §4 and §4a. It MUST then judge each receipt as one
billed use.

A billed use is verified only when its signature is valid, a disclosed
usage action hashes to its `action_canonical_hash`, and that action's
`passage_sha256` names a passage in the payee's own content.

A verifier MUST report every rejected use with its reject code, and MUST
NOT stop at the first rejected use.

This section verifies receipts. Pricing, settlement, and payment flows
such as HTTP 402 are out of scope.

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
| `delegation_missing`       | cited authorizing receipt is absent or later.    |
| `delegation_mismatch`      | authorizing receipt came from someone else, or   |
|                            | granted authority to a different sender.         |
| `usage_hash_mismatch`      | no disclosed usage action hashes to the          |
|                            | receipt's `action_canonical_hash`.               |
| `usage_passage_unknown`    | the usage action's passage is not in the payee's |
|                            | content.                                         |

`usage_hash_mismatch` and `usage_passage_unknown` are per-use codes
(§4b). The reference `verify-usage` command reports them, and
`signature_invalid`, against each rejected use and keeps going. It exits
0 when every billed use verifies and 1 when any use is rejected. Any
other code ends the run with its own exit code, as in `verify-chain`.

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
