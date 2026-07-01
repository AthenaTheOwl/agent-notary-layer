"""Golden-master locks on the RFC 8785 canonicalizer.

The receipt signature covers these bytes, so the exact serialization is a
wire-format contract: any drift silently invalidates existing signatures.
The literals below are the current output; changing them means changing the
canonicalization, which must be a deliberate, reviewed act.
"""

from __future__ import annotations

from notary.canonical import canonicalize


def test_object_keys_sort_by_utf16_code_unit():
    # RFC 8785 3.2.3 orders keys by UTF-16 code units, not by code point.
    # A supplementary-plane key (U+1F600) encodes to a surrogate pair whose
    # lead unit 0xD83D sorts before the BMP private-use key U+E000. A code
    # point comparison (or a utf-8 substitution) would flip these two, so the
    # pinned bytes distinguish the correct utf-16-be sort from the wrong one.
    assert canonicalize({"\U0001F600": 1, "\uE000": 2}) == (
        b'{"\xf0\x9f\x98\x80":1,"\xee\x80\x80":2}'
    )
