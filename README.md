# agent-notary-layer

Flip one hex digit of the action hash and the ed25519 signature stops verifying.
The receipt that proves one agent told another to commit a purchase order is eight
fields of JSON and a signature, and it carries none of the business payload it
attests. A regulator can replay it and learn that the action happened, in what order,
without ever seeing what was bought.

## What it does

When two organizations let their agents transact — a PO commit, a payment
authorization, a contract redline accepted — something has to survive the dispute
that comes later. The receiver attests it received the instruction. The hash chains
to the prior receipt so the order can't be reshuffled. The signature breaks the
moment a field is altered. A2A and Stripe's agent payment work defined the messages
agents exchange and defined no schema for the receipt of having exchanged them. This
is that receipt.

It's a schema-first repo. Three artifacts carry it: `spec/agent-receipt.schema.json`
is the receipt format; `src/notary/` is a reference verifier that checks a receipt
against the schema and replays its signature; `conformance/` holds the positive and
negative fixtures any third-party verifier has to reproduce to claim it conforms.
The receipt holds receiver identity, sender identity, the action's canonical hash,
the prior-receipt hash, a timestamp, and the signature — and nothing about the
underlying deal. v0.1 is implemented and tested; the canonicalizer follows RFC 8785.

## Try it

```bash
uv run notary show
```

```
notary demo -- verifying bundled conformance receipts
  keys: E:\claude_code\random-apps\agent-notary-layer\keys
  conformance: E:\claude_code\random-apps\agent-notary-layer\conformance

positive (expected: ACCEPT)
  [PASS] chained-second.json    -> accept (signature + schema valid)
  [PASS] chained-third.json     -> accept (signature + schema valid)
  [PASS] minimal.json           -> accept (signature + schema valid)

negative (expected: REJECT -- tamper/format detection)
  [PASS] bad-hash-format.json   -> reject (bad_canonical_hash_format: action_canonical_hash: 'md5:e3b0c44298fc1c149afbf4c8996fb924' does not match '^sha256:[0-9a-f]{64}$')
  [PASS] bad-timestamp.json     -> reject (schema_invalid: timestamp: '2026-07-04 14:22:31+00:00' does not match '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$')
  [PASS] bad-ulid.json          -> reject (schema_invalid: receipt_id: 'not-a-ulid' does not match '^[0-9A-HJKMNP-TV-Z]{26}$')
  [PASS] extra-field.json       -> reject (schema_invalid: <root>: Additional properties are not allowed ('payload' was unexpected))
  [PASS] missing-signature.json -> reject (schema_invalid: <root>: 'signature' is a required property)
  [PASS] wrong-algorithm.json   -> reject (schema_invalid: signature_algorithm: 'rsa-pss' is not one of ['ed25519'])

tamper check (flip one hex digit of a passing receipt)
  [PASS] chained-second.json: tamper rejected -> signature_invalid

RESULT: all receipts behaved as expected (tamper detection working).
```

The positives must accept, the negatives must reject, and the last line flips one
hex digit of a receipt that just passed to watch the signature fail. That row is the
whole argument.

More ways in:

```bash
uv sync
# verify a single receipt against the committed demo keys
uv run notary verify conformance/positive/minimal.json --keys-dir keys
# verify a directory of receipts forming one linear chain
uv run notary verify-chain conformance/positive --keys-dir keys
# no-arg demo: verify every bundled conformance receipt and report
uv run notary show
```

`python -m notary <subcommand>` works the same way (the package ships a `__main__`).
Run `uv run notary --help` for the full list: `verify`, `verify-chain`, `show`
(alias `demo`).

`notary verify` resolves the signer's public key from `--keys-dir` (default
`./keys`): one file per identity, named with the percent-encoded identity plus
`.pub`, holding base64 of the 32-byte ed25519 public key. The committed `keys/`
directory holds the synthetic demo keys for the conformance fixtures — not secret.

There is no `conformance` subcommand. The suite is just the fixtures under
`conformance/`, which `notary show` walks and `tests/test_conformance.py` runs
through the verifier.

## Tests

```bash
uv run pytest -q
```

## Live demo

`streamlit_app.py` wraps the reference verifier as a page: pick a committed
conformance receipt or paste your own, verify it (schema, signer resolution,
ed25519 signature), see the linear chain, and trip the live tamper check by flipping
one hex digit of the action hash. It runs entirely off the committed fixtures and
demo keys — no network, no secrets.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Deploy on Streamlit Community Cloud: New app -> this repo, branch `main`, main file
`streamlit_app.py`. `requirements.txt` pulls `streamlit` plus the verifier's runtime
deps (`jsonschema`, `PyNaCl`).

<!-- live-url: (add the streamlit cloud url here once deployed) -->

## How it connects

- [procurement-negotiation-lab](https://github.com/AthenaTheOwl/procurement-negotiation-lab)
  — the simulator where the PO commits and payment authorizations get made. This
  layer is the receipt those commitments would leave behind.

## Layout

```
agent-notary-layer/
  spec/
    agent-receipt.schema.json   # the receipt JSON Schema (v0.1)
    RFC-001-receipt-format.md   # the human-readable RFC
  src/notary/
    canonical.py                # RFC 8785 JCS canonicalizer
    verifier.py                 # schema + key + signature + chain checks
    cli.py                      # verify / verify-chain / show
    __main__.py                 # enables `python -m notary`
  conformance/
    positive/                   # fixtures that must accept
    negative/                   # fixtures that must reject
  keys/                         # synthetic demo public keys for the fixtures
  tests/                        # unit + end-to-end conformance tests
  streamlit_app.py              # live demo (Streamlit Community Cloud)
  requirements.txt              # demo deps
  examples/
    pactum_replay/              # worked example (pending)
  specs/                        # design specs
  docs/first-pr.md
  AGENTS.md
  LICENSE
  README.md
```

## License

MIT for the verifier code (see `LICENSE`). The schema and the RFC are intended as
CC-BY-4.0; a dedicated `spec/LICENSE.md` recording that split is still pending.
</content>
</invoke>
