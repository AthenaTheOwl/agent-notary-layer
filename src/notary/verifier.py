"""Schema, key, signature, and chain verification for agent receipts."""

from __future__ import annotations

import base64
import binascii
import json
import pathlib
import urllib.parse
from typing import Optional

from notary.canonical import signed_bytes

REJECT_CODES: dict[str, int] = {
    "schema_invalid": 2,
    "bad_canonical_hash_format": 3,
    "unknown_signer": 4,
    "signature_invalid": 5,
    "chain_not_linear": 6,
    "chain_break": 7,
    "chain_no_root": 8,
    "cycle_detected": 9,
    "key_malformed": 10,
}


class VerifyError(Exception):
    """Base class for all reject conditions. Carries the reject code."""

    code: str = "internal_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class SchemaLoadError(RuntimeError):
    """Packaging error: schema file missing or unreadable."""


class SchemaInvalid(VerifyError):
    code = "schema_invalid"


class BadCanonicalHashFormat(VerifyError):
    code = "bad_canonical_hash_format"


class UnknownSigner(VerifyError):
    code = "unknown_signer"


class SignatureInvalid(VerifyError):
    code = "signature_invalid"


class KeyMalformed(VerifyError):
    code = "key_malformed"


class ChainNotLinear(VerifyError):
    code = "chain_not_linear"


class ChainBreak(VerifyError):
    code = "chain_break"


class ChainNoRoot(VerifyError):
    code = "chain_no_root"


class CycleDetected(VerifyError):
    code = "cycle_detected"


_SCHEMA_CACHE: Optional[dict] = None
_VALIDATOR_CACHE = None
_HASH_FIELD = "action_canonical_hash"


def _schema_path() -> pathlib.Path:
    """Locate the packaged schema file.

    Tries the in-tree path first (so tests work without install) and
    falls back to the wheel-installed location.
    """
    here = pathlib.Path(__file__).resolve().parent
    in_tree = here.parent.parent / "spec" / "agent-receipt.schema.json"
    if in_tree.is_file():
        return in_tree
    packaged = here / "_data" / "agent-receipt.schema.json"
    if packaged.is_file():
        return packaged
    raise SchemaLoadError(f"agent-receipt.schema.json not found near {here}")


def load_schema() -> dict:
    """Read the JSON Schema document from disk. Cached after first call."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        path = _schema_path()
        try:
            _SCHEMA_CACHE = json.loads(path.read_text(encoding="utf-8"))
        except OSError as e:
            raise SchemaLoadError(f"cannot read schema at {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise SchemaLoadError(f"schema at {path} is not valid JSON: {e}") from e
    return _SCHEMA_CACHE


def _validator():
    global _VALIDATOR_CACHE
    if _VALIDATOR_CACHE is None:
        from jsonschema import Draft202012Validator

        schema = load_schema()
        Draft202012Validator.check_schema(schema)
        _VALIDATOR_CACHE = Draft202012Validator(schema)
    return _VALIDATOR_CACHE


def validate(receipt: dict) -> None:
    """Raise SchemaInvalid or BadCanonicalHashFormat if `receipt` fails."""
    validator = _validator()
    errors = sorted(validator.iter_errors(receipt), key=lambda e: e.path)
    if not errors:
        return

    # If the ONLY failure is the canonical-hash regex, route to a
    # distinct reject code so callers can differentiate.
    hash_only = all(
        list(e.absolute_path) == [_HASH_FIELD] and e.validator == "pattern"
        for e in errors
    )
    first = errors[0]
    rule = "/".join(str(p) for p in first.absolute_path) or "<root>"
    msg = f"{rule}: {first.message}"
    if hash_only:
        raise BadCanonicalHashFormat(msg)
    raise SchemaInvalid(msg)


class FileKeyResolver:
    """Maps `sender_identity` to a public key file under `root`.

    The filename is the percent-encoded identity + `.pub`. The file
    body is base64 of a 32-byte ed25519 public key.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self.root = pathlib.Path(root)

    def _path_for(self, sender_identity: str) -> pathlib.Path:
        # quote() with safe="" percent-encodes every reserved char, so
        # ":" / "/" in DIDs become %3A / %2F.
        encoded = urllib.parse.quote(sender_identity, safe="")
        return self.root / f"{encoded}.pub"

    def resolve(self, sender_identity: str) -> bytes:
        path = self._path_for(sender_identity)
        if not path.is_file():
            raise UnknownSigner(f"no key file for {sender_identity!r} at {path}")
        try:
            raw = base64.b64decode(path.read_text(encoding="utf-8").strip(), validate=True)
        except (binascii.Error, ValueError) as e:
            raise KeyMalformed(f"{path}: not valid base64: {e}") from e
        if len(raw) != 32:
            raise KeyMalformed(f"{path}: expected 32 bytes, got {len(raw)}")
        return raw


def verify_signature(pubkey: bytes, message: bytes, sig_b64: str) -> None:
    """Verify an ed25519 signature. Raise SignatureInvalid on mismatch."""
    if len(pubkey) != 32:
        raise KeyMalformed(f"public key must be 32 bytes, got {len(pubkey)}")
    try:
        sig = base64.b64decode(sig_b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise SignatureInvalid(f"signature is not valid base64: {e}") from e
    if len(sig) != 64:
        raise SignatureInvalid(f"signature must be 64 bytes, got {len(sig)}")

    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey

    try:
        VerifyKey(pubkey).verify(message, sig)
    except BadSignatureError as e:
        raise SignatureInvalid("ed25519 verify failed") from e


def verify_receipt(receipt: dict, resolver: FileKeyResolver) -> None:
    """Full single-receipt verification pipeline.

    Steps: schema -> key resolution -> canonicalize -> signature check.
    Raises a `VerifyError` subclass on any failure.
    """
    validate(receipt)
    pubkey = resolver.resolve(receipt["sender_identity"])
    message = signed_bytes(receipt)
    verify_signature(pubkey, message, receipt["signature"])


def order_and_check(receipts: list[dict]) -> list[dict]:
    """Topologically order receipts root-first and reject broken chains.

    Does NOT run per-receipt signature verification; the caller is
    expected to invoke `verify_receipt` on each element of the result.
    """
    if not receipts:
        raise ChainNoRoot("no receipts in input")

    by_id: dict[str, dict] = {}
    for r in receipts:
        rid = r.get("receipt_id")
        if not isinstance(rid, str):
            raise SchemaInvalid("receipt missing receipt_id")
        if rid in by_id:
            raise ChainNotLinear(f"duplicate receipt_id {rid!r}")
        by_id[rid] = r

    # Detect cycles in the prior-pointer graph BEFORE checking for a
    # root, so a pure cycle (no node with prior=null) reports cycle
    # rather than missing-root.
    for start in by_id.values():
        seen: set[str] = set()
        cur: Optional[dict] = start
        while cur is not None:
            cid = cur["receipt_id"]
            if cid in seen:
                raise CycleDetected(f"cycle re-enters {cid!r}")
            seen.add(cid)
            prior = cur.get("prior_receipt_id")
            if prior is None:
                break
            cur = by_id.get(prior)  # None means missing parent; caught below

    roots = [r for r in receipts if r.get("prior_receipt_id") is None]
    if len(roots) == 0:
        raise ChainNoRoot("no receipt has prior_receipt_id=null")
    if len(roots) > 1:
        raise ChainNotLinear(f"{len(roots)} roots; expected exactly one")

    # Build successor index. A linear chain requires each node to have
    # at most one successor.
    successors: dict[str, list[str]] = {rid: [] for rid in by_id}
    for r in receipts:
        prior = r.get("prior_receipt_id")
        if prior is None:
            continue
        if prior not in by_id:
            raise ChainBreak(
                f"receipt {r['receipt_id']!r} names missing predecessor {prior!r}"
            )
        successors[prior].append(r["receipt_id"])

    for parent, kids in successors.items():
        if len(kids) > 1:
            raise ChainNotLinear(
                f"receipt {parent!r} has multiple successors: {kids!r}"
            )

    ordered: list[dict] = []
    cur_id: Optional[str] = roots[0]["receipt_id"]
    while cur_id is not None:
        ordered.append(by_id[cur_id])
        kids = successors[cur_id]
        cur_id = kids[0] if kids else None

    if len(ordered) != len(receipts):
        unreached = set(by_id) - {r["receipt_id"] for r in ordered}
        raise ChainBreak(f"unreachable receipts: {sorted(unreached)!r}")

    return ordered
