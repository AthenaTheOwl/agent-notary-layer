"""Usage actions (RFC-001 §4b): check billed uses against the payee's own content.

A usage receipt is an ordinary receipt whose `action_canonical_hash` covers a
usage action `{kind: "usage", passage_sha256, answer_id, source_id}`. The payer
discloses the actions beside the receipts; the payee recomputes each hash and
looks the cited passage up in its own text.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

from notary.canonical import canonicalize
from notary.verifier import SchemaInvalid, VerifyError

ACTION_FIELDS = ("answer_id", "kind", "passage_sha256", "source_id")
CONTENT_SUFFIX = ".txt"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class UsageInputError(ValueError):
    """The content directory or actions file cannot be read."""


class UsageHashMismatch(VerifyError):
    code = "usage_hash_mismatch"


class UsagePassageUnknown(VerifyError):
    code = "usage_passage_unknown"


# Per-use reject codes and the words `verify-usage` prints for them.
USAGE_REASONS: dict[str, str] = {
    "signature_invalid": "bad signature",
    "usage_hash_mismatch": "hash mismatch",
    "usage_passage_unknown": "passage not in payee content",
}


def split_passages(text: str) -> list[str]:
    """Split text into passages by the single rule in RFC-001 §4b.

    A leading byte-order mark is dropped and CRLF / CR become LF. A blank
    line is empty or holds only spaces and tabs. A passage is a maximal run
    of non-blank lines, kept as written and joined with LF.
    """
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    passages: list[str] = []
    run: list[str] = []
    for line in text.split("\n"):
        if line.strip(" \t"):
            run.append(line)
        elif run:
            passages.append("\n".join(run))
            run = []
    if run:
        passages.append("\n".join(run))
    return passages


def passage_sha256(passage: str) -> str:
    """Lowercase hex SHA-256 over the passage's UTF-8 bytes."""
    return hashlib.sha256(passage.encode("utf-8")).hexdigest()


def load_payee_passages(content_dir: pathlib.Path) -> set[str]:
    """Hash every passage in every `.txt` file under `content_dir`."""
    content_dir = pathlib.Path(content_dir)
    if not content_dir.is_dir():
        raise UsageInputError(f"{content_dir} is not a directory")
    files = sorted(p for p in content_dir.rglob("*" + CONTENT_SUFFIX) if p.is_file())
    if not files:
        raise UsageInputError(f"no {CONTENT_SUFFIX} files under {content_dir}")
    hashes: set[str] = set()
    for f in files:
        try:
            text = f.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise UsageInputError(f"{f}: {e}") from e
        hashes.update(passage_sha256(p) for p in split_passages(text))
    return hashes


def validate_usage_action(action: object, where: str) -> None:
    """Raise SchemaInvalid unless `action` is a well-formed usage action."""
    if not isinstance(action, dict):
        raise SchemaInvalid(f"{where}: usage action is not a JSON object")
    if tuple(sorted(action)) != ACTION_FIELDS:
        raise SchemaInvalid(f"{where}: usage action fields must be exactly {list(ACTION_FIELDS)}")
    if action["kind"] != "usage":
        raise SchemaInvalid(f"{where}: kind must be 'usage', got {action['kind']!r}")
    if not isinstance(action["passage_sha256"], str) or not _HEX64.match(action["passage_sha256"]):
        raise SchemaInvalid(f"{where}: passage_sha256 must be 64 lowercase hex chars")
    for field in ("answer_id", "source_id"):
        if not isinstance(action[field], str) or not action[field]:
            raise SchemaInvalid(f"{where}: {field} must be a non-empty string")


def action_canonical_hash(action: dict) -> str:
    """`sha256:` + hex SHA-256 over the RFC 8785 form of the action."""
    return "sha256:" + hashlib.sha256(canonicalize(action)).hexdigest()


def load_actions(path: pathlib.Path) -> dict[str, dict]:
    """Read a JSON Lines file of usage actions, keyed by canonical hash."""
    path = pathlib.Path(path)
    try:
        lines = path.read_bytes().decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise UsageInputError(f"{path}: {e}") from e
    by_hash: dict[str, dict] = {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"{path.name} line {n}"
        try:
            action = json.loads(line)
        except json.JSONDecodeError as e:
            raise SchemaInvalid(f"{where}: {e}") from e
        validate_usage_action(action, where)
        by_hash[action_canonical_hash(action)] = action
    return by_hash


def check_use(receipt: dict, actions_by_hash: dict[str, dict], passages: set[str]) -> dict:
    """Judge one signature-verified receipt as a billed use.

    Returns the disclosed action when the use verifies. Raises
    UsageHashMismatch when no disclosed action hashes to the receipt's
    `action_canonical_hash`, and UsagePassageUnknown when the action cites a
    passage the payee does not hold.
    """
    action = actions_by_hash.get(receipt["action_canonical_hash"])
    if action is None:
        raise UsageHashMismatch(
            f"{receipt['receipt_id']!r}: no disclosed usage action hashes to "
            f"{receipt['action_canonical_hash']}"
        )
    if action["passage_sha256"] not in passages:
        raise UsagePassageUnknown(
            f"{receipt['receipt_id']!r}: passage {action['passage_sha256']} "
            "is not in the payee's content"
        )
    return action


def summarize(billed: int, rejected_codes: list[str]) -> str:
    """One line: `billed N, verified N, rejected N (reasons)`."""
    line = f"billed {billed}, verified {billed - len(rejected_codes)}, rejected {len(rejected_codes)}"
    if not rejected_codes:
        return line
    counts = {code: rejected_codes.count(code) for code in USAGE_REASONS if code in rejected_codes}
    if len(counts) == 1:
        return f"{line} ({USAGE_REASONS[next(iter(counts))]})"
    return line + " (" + ", ".join(f"{USAGE_REASONS[c]}: {n}" for c, n in counts.items()) + ")"
