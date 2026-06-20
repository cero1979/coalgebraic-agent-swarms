#!/usr/bin/env python3
"""Verify every file hash recorded in a generated artefact manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    repository_root = manifest_path.parents[2]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for name, expected in sorted(manifest.get("sha256", {}).items()):
        path = repository_root / name
        if not path.is_file():
            failures.append(f"missing: {name}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            failures.append(f"checksum mismatch: {name}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1

    print(f"OK {len(manifest.get('sha256', {}))} manifest entries verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
