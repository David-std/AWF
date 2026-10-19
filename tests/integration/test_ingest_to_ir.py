"""End-to-end Sprint 1 integration without a network or ML provider."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.blob_store import BlobIntegrityError, FileBlobStore
from awf.application.commands.ingest_document import ingest_document
from awf.cli.main import main


def test_ingest_is_reproducible_and_original_unchanged(tmp_path, capsys) -> None:
    raw = "# Diseño\n\nUn resultado del 18 % [1].\n".encode()
    src = tmp_path / "thesis.md"
    src.write_bytes(raw)
    store_root = tmp_path / "blobs"
    output = tmp_path / "out.json"

    assert main(["ingest", str(src), "--store", str(store_root), "--output", str(output)]) == 0
    first = json.loads(output.read_text(encoding="utf-8"))
    assert first["sha256"] == hashlib.sha256(raw).hexdigest()
    assert first["blocks"][1]["text"] == "Un resultado del 18 % [1]."
    assert src.read_bytes() == raw

    blob = store_root / first["sha256"][:2] / first["sha256"]
    assert blob.read_bytes() == raw
    assert main(["ingest", str(src), "--store", str(store_root), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == first
    assert src.read_bytes() == raw
    assert capsys.readouterr().err == ""


def test_cli_rejects_overwrite_of_input(tmp_path, capsys) -> None:
    source = tmp_path / "input.md"
    source.write_text("Protected", encoding="utf-8")
    assert main(["ingest", str(source), "--output", str(source)]) == 2
    assert source.read_text(encoding="utf-8") == "Protected"
    assert "SOURCE_PROTECTED" in capsys.readouterr().err


def test_unknown_extension_is_rejected(tmp_path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("Not Markdown", encoding="utf-8")
    try:
        ingest_document(source, parser=MarkdownAdapter())
    except ValueError as exc:
        assert ".md" in str(exc)
    else:
        raise AssertionError("unsupported extension accepted")


def test_blob_integrity_error_on_tampered_stored_copy(tmp_path) -> None:
    raw = b"original"
    storage = FileBlobStore(tmp_path)
    digest = storage.put(raw)
    path = storage.path_for(digest)
    path.write_bytes(b"tampered")
    try:
        storage.put(raw)
    except BlobIntegrityError:
        pass
    else:
        raise AssertionError("tampered blob accepted")


def test_json_to_stdout_when_output_not_specified(tmp_path, capsys) -> None:
    source = tmp_path / "x.md"
    source.write_text("hello", encoding="utf-8")
    assert main(["ingest", str(source)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["blocks"][0]["kind"] == "paragraph"
    assert not (tmp_path / "blobs").exists()


def test_output_hardlink_cannot_overwrite_original(tmp_path, capsys) -> None:
    source = tmp_path / "original.md"
    source.write_bytes(b"protected original")
    alias = tmp_path / "alias.json"
    try:
        os.link(source, alias)
    except OSError:
        pytest.skip("this filesystem does not support hard links")
    assert main(["ingest", str(source), "--output", str(alias)]) == 2
    assert source.read_bytes() == b"protected original"
    assert alias.read_bytes() == b"protected original"
    assert "SOURCE_PROTECTED" in capsys.readouterr().err


def test_output_replace_failure_preserves_prior_result(tmp_path, monkeypatch, capsys) -> None:
    source = tmp_path / "original.md"
    source.write_text("a paragraph", encoding="utf-8")
    destination = tmp_path / "result.json"
    destination.write_bytes(b"previous valid result")

    def fail_replace(_source, _destination) -> None:
        raise OSError("simulated interrupted publication")

    monkeypatch.setattr("awf.cli.main.os.replace", fail_replace)
    assert main(["ingest", str(source), "--output", str(destination)]) == 2
    assert destination.read_bytes() == b"previous valid result"
    assert source.read_text(encoding="utf-8") == "a paragraph"
    assert not list(tmp_path.glob(".awf-*"))
    assert "INGEST_FAILED" in capsys.readouterr().err


def test_blob_rejects_symlinked_hash_directory(tmp_path) -> None:
    root = tmp_path / "private"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    raw = b"confidential synthetic bytes"
    digest = hashlib.sha256(raw).hexdigest()
    try:
        (root / digest[:2]).symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("creating directory symlinks requires additional OS privileges")
    with pytest.raises(BlobIntegrityError, match="escapes"):
        FileBlobStore(root).put(raw)
    assert not (external / digest).exists()


def test_blob_rejects_existing_symlink_even_when_content_matches(tmp_path) -> None:
    root = tmp_path / "private"
    raw = b"existing content"
    digest = hashlib.sha256(raw).hexdigest()
    target = tmp_path / "other"
    target.write_bytes(raw)
    destination = root / digest[:2] / digest
    destination.parent.mkdir(parents=True)
    try:
        destination.symlink_to(target)
    except OSError:
        pytest.skip("creating symlinks requires additional OS privileges")
    with pytest.raises(BlobIntegrityError, match="wrong content"):
        FileBlobStore(root).put(raw)


def test_concurrent_blob_writers_publish_only_complete_originals(tmp_path) -> None:
    store = FileBlobStore(tmp_path / "private")
    raw = b"synthetic academic source\n" * 65_536
    expected = hashlib.sha256(raw).hexdigest()
    with ThreadPoolExecutor(max_workers=12) as pool:
        digests = list(pool.map(store.put, [raw] * 24))
    assert digests == [expected] * 24
    assert store.path_for(expected).read_bytes() == raw
    assert not list(store.path_for(expected).parent.glob(".awf-*"))
