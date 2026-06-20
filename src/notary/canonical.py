"""RFC 8785 JSON Canonicalization Scheme (JCS).

Vendored rather than taking a dependency: the Python ecosystem's JCS
packages are unmaintained, and the rules are short enough to inline
with the RFC section numbers in comments.

Covers the subset needed for receipt canonicalization: strings, nulls,
booleans, integers, finite floats, lists, and dicts with string keys.
Receipts only use strings and null in v0.1, so number handling is
defensive but not exhaustively ES6-faithful for extreme floats.
"""

from __future__ import annotations

import math
from typing import Any


class CanonError(ValueError):
    """Raised when a value cannot be canonicalized per RFC 8785."""


def _serialize_string(s: str) -> str:
    # RFC 8785 §3.2.2.2: escape only ", \, and U+0000-U+001F.
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif cp < 0x20:
            out.append("\\u%04x" % cp)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _serialize_number(n: Any) -> str:
    # RFC 8785 §3.2.2.3: ES6 ToString(Number).
    if isinstance(n, bool):
        # bool is a subclass of int in Python; route to boolean serialization.
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if math.isnan(n) or math.isinf(n):
        raise CanonError("NaN/Infinity not representable in JCS")
    if n == 0:
        return "0"
    if n.is_integer() and abs(n) < 1e21:
        return str(int(n))
    # repr() does not exactly match ES6 number formatting, but receipts
    # in v0.1 carry no floats; this branch exists only for completeness.
    return repr(n)


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _serialize_number(value)
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(v) for v in value) + "]"
    if isinstance(value, dict):
        # RFC 8785 §3.2.3: sort keys by UTF-16 code-unit ordering.
        for k in value:
            if not isinstance(k, str):
                raise CanonError("Object keys must be strings")
        items = sorted(value.items(), key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(_serialize_string(k) + ":" + _serialize(v) for k, v in items) + "}"
    raise CanonError(f"Unsupported type: {type(value).__name__}")


def canonicalize(value: Any) -> bytes:
    """Return the RFC 8785 JCS form of `value` as UTF-8 bytes."""
    return _serialize(value).encode("utf-8")


def signed_bytes(receipt: dict) -> bytes:
    """Return the canonical bytes that the receipt's signature covers.

    The `signature` field is omitted; everything else is canonicalized.
    """
    body = {k: v for k, v in receipt.items() if k != "signature"}
    return canonicalize(body)
