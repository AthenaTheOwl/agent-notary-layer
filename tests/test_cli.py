"""CLI end-to-end tests: argument parsing, exit codes, accept/reject output."""

from __future__ import annotations

import json
import pathlib

import pytest

from notary import cli


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_no_args_errors(capsys):
    with pytest.raises(SystemExit):
        cli.main([])


def test_verify_accepts_signed_receipt(
    make_signed_receipt, write_receipt, keys_dir, capsys
):
    path = write_receipt(make_signed_receipt())
    code, out, err = _run(["verify", str(path), "--keys-dir", str(keys_dir)], capsys)
    assert code == 0
    assert out.strip() == "accept"


def test_verify_rejects_schema_invalid(write_receipt, keys_dir, capsys):
    bad = {"not": "a receipt"}
    path = write_receipt(bad)
    code, out, err = _run(["verify", str(path), "--keys-dir", str(keys_dir)], capsys)
    assert code == 2
    assert "schema_invalid" in err


def test_verify_rejects_bad_canonical_hash_format(
    make_signed_receipt, write_receipt, keys_dir, capsys
):
    receipt = make_signed_receipt()
    receipt["action_canonical_hash"] = "md5:" + "0" * 32
    path = write_receipt(receipt)
    code, out, err = _run(["verify", str(path), "--keys-dir", str(keys_dir)], capsys)
    assert code == 3
    assert "bad_canonical_hash_format" in err


def test_verify_rejects_unknown_signer(
    make_signed_receipt, write_receipt, tmp_path, capsys
):
    path = write_receipt(make_signed_receipt())
    empty_keys = tmp_path / "empty-keys"
    empty_keys.mkdir()
    code, out, err = _run(
        ["verify", str(path), "--keys-dir", str(empty_keys)], capsys
    )
    assert code == 4
    assert "unknown_signer" in err


def test_verify_rejects_signature_invalid(
    make_signed_receipt, write_receipt, keys_dir, capsys
):
    receipt = make_signed_receipt()
    # Tampering the hash invalidates the signature over the canonical bytes.
    receipt["action_canonical_hash"] = "sha256:" + "f" * 64
    path = write_receipt(receipt)
    code, out, err = _run(["verify", str(path), "--keys-dir", str(keys_dir)], capsys)
    assert code == 5
    assert "signature_invalid" in err


def test_verify_rejects_unparseable_json(tmp_path, keys_dir, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    code, out, err = _run(["verify", str(bad), "--keys-dir", str(keys_dir)], capsys)
    assert code == 2  # schema_invalid covers parse failure


def test_verify_chain_accepts_three(
    make_signed_receipt, keys_dir, tmp_path, capsys
):
    chain_dir = tmp_path / "chain"
    chain_dir.mkdir()
    r1 = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id=None,
        timestamp="2026-07-04T14:22:31Z",
    )
    r2 = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id=r1["receipt_id"],
        timestamp="2026-07-04T14:22:32Z",
    )
    r3 = make_signed_receipt(
        receipt_id="01J7Z9PM4Q2X3F0K0F0A0J3T20",
        prior_receipt_id=r2["receipt_id"],
        timestamp="2026-07-04T14:22:33Z",
    )
    for i, r in enumerate([r1, r2, r3]):
        (chain_dir / f"{i:03d}.json").write_text(json.dumps(r), encoding="utf-8")
    code, out, err = _run(
        ["verify-chain", str(chain_dir), "--keys-dir", str(keys_dir)], capsys
    )
    assert code == 0, err
    assert out.strip() == "accept (3 receipts)"


def test_verify_chain_rejects_two_roots(
    make_signed_receipt, keys_dir, tmp_path, capsys
):
    chain_dir = tmp_path / "two-roots"
    chain_dir.mkdir()
    r1 = make_signed_receipt(receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y")
    r2 = make_signed_receipt(receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z")
    for i, r in enumerate([r1, r2]):
        (chain_dir / f"{i:03d}.json").write_text(json.dumps(r), encoding="utf-8")
    code, out, err = _run(
        ["verify-chain", str(chain_dir), "--keys-dir", str(keys_dir)], capsys
    )
    assert code == 6
    assert "chain_not_linear" in err


def test_verify_chain_rejects_missing_parent(
    make_signed_receipt, keys_dir, tmp_path, capsys
):
    chain_dir = tmp_path / "broken"
    chain_dir.mkdir()
    r1 = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y", prior_receipt_id=None
    )
    r2 = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4Q2X3F0K0F0A0J3T20",
    )
    for i, r in enumerate([r1, r2]):
        (chain_dir / f"{i:03d}.json").write_text(json.dumps(r), encoding="utf-8")
    code, out, err = _run(
        ["verify-chain", str(chain_dir), "--keys-dir", str(keys_dir)], capsys
    )
    assert code == 7
    assert "chain_break" in err


def test_verify_chain_rejects_no_root(
    make_signed_receipt, keys_dir, tmp_path, capsys
):
    chain_dir = tmp_path / "no-root"
    chain_dir.mkdir()
    only = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id="01J7Z9PM4Z2X3F0K0F0A0J3T20",  # not in dir
    )
    (chain_dir / "001.json").write_text(json.dumps(only), encoding="utf-8")
    code, out, err = _run(
        ["verify-chain", str(chain_dir), "--keys-dir", str(keys_dir)], capsys
    )
    assert code == 8
    assert "chain_no_root" in err


def test_verify_chain_rejects_cycle(
    make_signed_receipt, keys_dir, tmp_path, capsys
):
    chain_dir = tmp_path / "cycle"
    chain_dir.mkdir()
    a = make_signed_receipt(
        receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
        prior_receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
    )
    b = make_signed_receipt(
        receipt_id="01J7Z9PM4P2X3F0K0F0A0J3T1Z",
        prior_receipt_id="01J7Z9PM4N2X3F0K0F0A0J3T1Y",
    )
    for i, r in enumerate([a, b]):
        (chain_dir / f"{i:03d}.json").write_text(json.dumps(r), encoding="utf-8")
    code, out, err = _run(
        ["verify-chain", str(chain_dir), "--keys-dir", str(keys_dir)], capsys
    )
    assert code == 9
    assert "cycle_detected" in err


def test_help_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "verify" in out
    assert "verify-chain" in out
