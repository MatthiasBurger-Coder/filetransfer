from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from seven_z_streamer.manifest import load_manifest
from seven_z_streamer.validators import parse_prefix, parse_size, parse_zstd_level


def test_parse_size_decimal_and_binary_units() -> None:
    assert parse_size("123") == 123
    assert parse_size("100M") == 100_000_000
    assert parse_size("100MiB") == 100 * 1024 * 1024
    assert parse_size("1.5G") == 1_500_000_000


def test_parse_size_rejects_invalid_values() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_size("0")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_size("10XB")


def test_parse_prefix_rejects_paths() -> None:
    assert parse_prefix("bigfolder-transfer") == "bigfolder-transfer"
    with pytest.raises(argparse.ArgumentTypeError):
        parse_prefix("../escape")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_prefix("nested/name")


def test_parse_zstd_level_range() -> None:
    assert parse_zstd_level("1") == 1
    assert parse_zstd_level("19") == 19
    with pytest.raises(argparse.ArgumentTypeError):
        parse_zstd_level("0")


def test_load_manifest_requires_contiguous_sequences(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        """
{
  "version": 1,
  "packages": [
    {"sequence": 1},
    {"sequence": 3}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="sequence"):
        load_manifest(manifest)


def test_load_manifest_rejects_path_traversal_package_name(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        """
{
  "version": 1,
  "packages": [
    {"sequence": 1, "name": "../escape.7z"}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="invalid package name"):
        load_manifest(manifest)


def test_load_manifest_reads_7z_manifest_package(monkeypatch, tmp_path) -> None:
    manifest_package = tmp_path / "demo-manifest.7z"
    manifest_package.write_bytes(b"placeholder")

    class FakeProcess:
        returncode = 0

        def communicate(self):
            return (
                b'{"version": 1, "package_count": 1, "packages": [{"sequence": 1, "name": "demo-000001.7z"}]}',
                b"",
            )

    monkeypatch.setattr("seven_z_streamer.manifest.require_toolchain", lambda use_zstd: SimpleNamespace(seven_zip="7z"))
    monkeypatch.setattr("seven_z_streamer.manifest.extract_file_to_stdout", lambda *args: FakeProcess())

    loaded = load_manifest(manifest_package)

    assert loaded["packages"][0]["name"] == "demo-000001.7z"
