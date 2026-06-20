"""argparse front-end for the notary verifier."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Optional, Sequence

from notary.verifier import (
    REJECT_CODES,
    ChainBreak,
    ChainNoRoot,
    ChainNotLinear,
    CycleDetected,
    FileKeyResolver,
    SchemaInvalid,
    SchemaLoadError,
    VerifyError,
    order_and_check,
    verify_receipt,
)


def _load_receipt(path: pathlib.Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SchemaInvalid(f"{path}: {e}") from e
    if not isinstance(data, dict):
        raise SchemaInvalid(f"{path}: top-level value is not a JSON object")
    return data


def _emit_reject(err: VerifyError) -> int:
    code = err.code
    exit_code = REJECT_CODES.get(code, 1)
    print(f"reject: {code}: {err}", file=sys.stderr)
    return exit_code


def cmd_verify(args: argparse.Namespace) -> int:
    receipt_path = pathlib.Path(args.path)
    keys_dir = pathlib.Path(args.keys_dir)
    try:
        receipt = _load_receipt(receipt_path)
        resolver = FileKeyResolver(keys_dir)
        verify_receipt(receipt, resolver)
    except VerifyError as e:
        return _emit_reject(e)
    print("accept")
    return 0


def cmd_verify_chain(args: argparse.Namespace) -> int:
    dir_path = pathlib.Path(args.directory)
    keys_dir = pathlib.Path(args.keys_dir)
    if not dir_path.is_dir():
        print(f"reject: schema_invalid: {dir_path} is not a directory", file=sys.stderr)
        return REJECT_CODES["schema_invalid"]

    files = sorted(p for p in dir_path.iterdir() if p.is_file() and p.suffix == ".json")
    receipts: list[dict] = []
    try:
        for fp in files:
            receipts.append(_load_receipt(fp))
        ordered = order_and_check(receipts)
        resolver = FileKeyResolver(keys_dir)
        prev_id: Optional[str] = None
        for r in ordered:
            verify_receipt(r, resolver)
            if prev_id is not None and r.get("prior_receipt_id") != prev_id:
                raise ChainBreak(
                    f"{r['receipt_id']!r}.prior_receipt_id != predecessor.receipt_id"
                )
            prev_id = r["receipt_id"]
    except VerifyError as e:
        return _emit_reject(e)

    print(f"accept ({len(ordered)} receipts)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="notary",
        description="Verify agent-receipt v0.1 documents and chains.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="verify a single receipt JSON file")
    v.add_argument("path", help="path to the receipt JSON file")
    v.add_argument(
        "--keys-dir",
        default="./keys",
        help="directory holding <percent-encoded-identity>.pub files (default: ./keys)",
    )
    v.set_defaults(func=cmd_verify)

    c = sub.add_parser(
        "verify-chain",
        help="verify a directory of receipts forming a linear chain",
    )
    c.add_argument("directory", help="directory containing receipt .json files")
    c.add_argument(
        "--keys-dir",
        default="./keys",
        help="directory holding <percent-encoded-identity>.pub files (default: ./keys)",
    )
    c.set_defaults(func=cmd_verify_chain)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SchemaLoadError as e:
        print(f"error: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
