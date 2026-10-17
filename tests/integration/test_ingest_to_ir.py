"""End-to-end Sprint 1 integration without a network or ML provider."""

from __future__ import annotations

import hashlib
import json

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
