"""Usage receipts (RFC-001 §4b): the committed billing period through the real CLI."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil

import pytest

from notary import cli
from notary.usage import (
    action_canonical_hash,
    passage_sha256,
    split_passages,
    summarize,
)
from notary.verifier import REJECT_CODES

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
USAGE = REPO_ROOT / "conformance" / "usage"
PERIOD = USAGE / "billing-period-01"
CONTENT = USAGE / "content"
KEYS_DIR = REPO_ROOT / "keys"


def _verify_usage(period: pathlib.Path, actions: pathlib.Path | None = None,
                  content: pathlib.Path = CONTENT) -> int:
    actions = actions or period / "actions.jsonl"
    return cli.main([
        "verify-usage", str(period),
        "--actions", str(actions),
        "--content", str(content),
        "--keys-dir", str(KEYS_DIR),
    ])


def _summary(capsys) -> str:
    return capsys.readouterr().out.strip().splitlines()[-1]


@pytest.fixture
def period_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    dest = tmp_path / "period"
    shutil.copytree(PERIOD, dest)
    return dest


def test_committed_period_rejects_the_passage_the_payee_does_not_hold(capsys):
    assert _verify_usage(PERIOD) == 1
    out = capsys.readouterr().out
    assert out.strip().splitlines()[-1] == "billed 3, verified 2, rejected 1 (passage not in payee content)"
    assert "01JA9000000000000000PAY003  passage not in payee content (usage_passage_unknown)" in out


def test_usage_receipts_are_ordinary_receipts(capsys):
    # No new receipt fields: the period is a plain chain to verify-chain.
    assert cli.main(["verify-chain", str(PERIOD), "--keys-dir", str(KEYS_DIR)]) == 0
    capsys.readouterr()


def test_honest_period_exits_zero(period_copy, capsys):
    (period_copy / "03.json").unlink()
    assert _verify_usage(period_copy) == 0
    assert _summary(capsys) == "billed 2, verified 2, rejected 0"


def test_edited_action_is_a_hash_mismatch(period_copy, capsys):
    actions_path = period_copy / "actions.jsonl"
    lines = actions_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["answer_id"] = "ans-9999"
    lines[0] = json.dumps(first)
    actions_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _verify_usage(period_copy) == 1
    assert _summary(capsys) == (
        "billed 3, verified 1, rejected 2 (hash mismatch: 1, passage not in payee content: 1)"
    )


def test_tampered_receipt_is_a_bad_signature_and_the_walk_continues(period_copy, capsys):
    path = period_copy / "02.json"
    r = json.loads(path.read_text(encoding="utf-8"))
    r["timestamp"] = "2026-10-03T16:41:00Z"
    path.write_text(json.dumps(r), encoding="utf-8")
    assert _verify_usage(period_copy) == 1
    assert _summary(capsys) == (
        "billed 3, verified 1, rejected 2 (bad signature: 1, passage not in payee content: 1)"
    )


def test_payee_dropping_a_passage_rejects_the_use(tmp_path, capsys):
    content = tmp_path / "content"
    content.mkdir()
    text = (CONTENT / "harbor-notes.txt").read_text(encoding="utf-8")
    kept = [p for i, p in enumerate(split_passages(text)) if i != 2]
    (content / "harbor-notes.txt").write_text("\n\n".join(kept) + "\n", encoding="utf-8")
    assert _verify_usage(PERIOD, content=content) == 1
    assert _summary(capsys) == "billed 3, verified 1, rejected 2 (passage not in payee content)"


def test_chain_failure_ends_the_run_with_its_own_code(period_copy, capsys):
    (period_copy / "01.json").unlink()
    assert _verify_usage(period_copy) == REJECT_CODES["chain_no_root"]
    capsys.readouterr()


def test_malformed_action_line_is_schema_invalid(period_copy, capsys):
    actions_path = period_copy / "actions.jsonl"
    with actions_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "usage", "passage_sha256": "abc", "answer_id": "a", "source_id": "s"}) + "\n")
    assert _verify_usage(period_copy) == REJECT_CODES["schema_invalid"]
    assert "actions.jsonl line 4" in capsys.readouterr().err


def test_missing_content_dir_is_an_input_error(tmp_path, capsys):
    assert _verify_usage(PERIOD, content=tmp_path / "nowhere") == 2
    assert "error:" in capsys.readouterr().err


def test_passage_rule_ignores_line_endings_bom_and_blank_runs():
    lf = "Title\n\nFirst line\nsecond line\n\n \t\n\nLast\n"
    crlf = "﻿" + lf.replace("\n", "\r\n")
    assert split_passages(lf) == ["Title", "First line\nsecond line", "Last"]
    assert split_passages(crlf) == split_passages(lf)


def test_action_hash_is_jcs_over_the_action():
    a = {"kind": "usage", "passage_sha256": passage_sha256("x"), "answer_id": "a", "source_id": "s"}
    reordered = dict(reversed(list(a.items())))
    assert action_canonical_hash(a) == action_canonical_hash(reordered)
    assert action_canonical_hash(a).startswith("sha256:")


def test_summary_line_with_no_rejections():
    assert summarize(3, []) == "billed 3, verified 3, rejected 0"


def test_fixtures_rebuild_from_the_synthetic_seed(tmp_path):
    """The signing key is derived at run time; the committed bundle is reproducible."""
    spec = importlib.util.spec_from_file_location(
        "make_usage_fixtures", REPO_ROOT / "scripts" / "make_usage_fixtures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(tmp_path)

    rebuilt = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert rebuilt, "generator wrote nothing"
    for rel in rebuilt:
        committed = (REPO_ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
        assert (tmp_path / rel).read_text(encoding="utf-8").replace("\r\n", "\n") == committed, rel
