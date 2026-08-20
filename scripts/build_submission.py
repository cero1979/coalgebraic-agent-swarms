#!/usr/bin/env python3
"""Build a flat, independently compilable Elsevier submission directory.

Editorial Manager handles LaTeX uploads most reliably when every uploaded source
file is at one level.  This builder follows ``\\input``, ``\\include``, graphics,
and bibliography dependencies from ``main.tex``, gives nested dependencies
collision-free flat names, and rewrites the corresponding references.  It also
preserves the author-maintained cover letter, submission README, and checklist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "submission" / "array"
AUTHOR_MAINTAINED = (
    "cover_letter.tex",
    "README_SUBMISSION.md",
    "submission_checklist.md",
)
FIXED_ELSEVIER_FILES = ("cas-sc.cls", "cas-common.sty")
GRAPHIC_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
BUILD_AUXILIARY_SUFFIXES = {
    ".aux",
    ".bbl",
    ".bcf",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".lof",
    ".log",
    ".lot",
    ".out",
    ".run.xml",
    ".synctex.gz",
    ".toc",
}

INPUT_RE = re.compile(r"\\(?P<command>input|include)\s*\{(?P<value>[^{}]+)\}")
GRAPHIC_RE = re.compile(
    r"\\includegraphics(?P<options>\s*\[[^]]*\])?\s*\{(?P<value>[^{}]+)\}"
)
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{(?P<value>[^{}]+)\}")
BIBSTYLE_RE = re.compile(r"\\bibliographystyle\s*\{(?P<value>[^{}]+)\}")


class SubmissionBuildError(RuntimeError):
    """Raised when a complete, unambiguous source bundle cannot be built."""


def _strip_comment(line: str) -> tuple[str, str]:
    """Split a TeX line at its first unescaped percent sign."""

    for index, char in enumerate(line):
        if char != "%":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return line[:index], line[index:]
    return line, ""


def _safe_relative(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve())
    except ValueError as error:
        raise SubmissionBuildError(
            f"dependency escapes the repository root: {path}"
        ) from error


def flat_name(path: Path, root: Path, *, main: Path) -> str:
    """Return a deterministic one-level name for a repository source file."""

    resolved = path.resolve()
    if resolved == main.resolve():
        return "main.tex"
    relative = _safe_relative(resolved, root)
    return "__".join(relative.parts)


def _resolve_dependency(
    reference: str,
    *,
    source: Path,
    root: Path,
    extensions: Sequence[str],
) -> Path:
    value = reference.strip()
    if not value or any(token in value for token in ("#", "\\", "{")):
        raise SubmissionBuildError(
            f"dynamic dependency cannot be flattened in {source}: {reference!r}"
        )
    candidate = Path(value)
    if candidate.is_absolute():
        candidates = [candidate]
    else:
        candidates = [source.parent / candidate, root / candidate]
    expanded: list[Path] = []
    for item in candidates:
        expanded.append(item)
        if not item.suffix:
            expanded.extend(Path(f"{item}{extension}") for extension in extensions)
    for item in expanded:
        if item.is_file():
            _safe_relative(item, root)
            return item.resolve()
    raise SubmissionBuildError(
        f"missing dependency {reference!r}, referenced by "
        f"{_safe_relative(source, root).as_posix()}"
    )


def _rewrite_tex(
    source: Path,
    *,
    root: Path,
    main: Path,
) -> tuple[str, set[Path]]:
    dependencies: set[Path] = set()

    def input_replacement(match: re.Match[str]) -> str:
        dependency = _resolve_dependency(
            match.group("value"),
            source=source,
            root=root,
            extensions=(".tex",),
        )
        dependencies.add(dependency)
        return f"\\{match.group('command')}{{{flat_name(dependency, root, main=main)}}}"

    def graphic_replacement(match: re.Match[str]) -> str:
        dependency = _resolve_dependency(
            match.group("value"),
            source=source,
            root=root,
            extensions=GRAPHIC_EXTENSIONS,
        )
        dependencies.add(dependency)
        return (
            f"\\includegraphics{match.group('options') or ''}"
            f"{{{flat_name(dependency, root, main=main)}}}"
        )

    def bibliography_replacement(match: re.Match[str]) -> str:
        rewritten: list[str] = []
        for reference in match.group("value").split(","):
            dependency = _resolve_dependency(
                reference,
                source=source,
                root=root,
                extensions=(".bib",),
            )
            dependencies.add(dependency)
            rewritten.append(Path(flat_name(dependency, root, main=main)).stem)
        return f"\\bibliography{{{','.join(rewritten)}}}"

    def style_replacement(match: re.Match[str]) -> str:
        value = match.group("value").strip()
        try:
            dependency = _resolve_dependency(
                value,
                source=source,
                root=root,
                extensions=(".bst",),
            )
        except SubmissionBuildError:
            # Standard TeX bibliography styles are resolved by the distribution.
            return match.group(0)
        dependencies.add(dependency)
        return f"\\bibliographystyle{{{Path(flat_name(dependency, root, main=main)).stem}}}"

    rewritten_lines: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        code, comment = _strip_comment(line)
        code = INPUT_RE.sub(input_replacement, code)
        code = GRAPHIC_RE.sub(graphic_replacement, code)
        code = BIBLIOGRAPHY_RE.sub(bibliography_replacement, code)
        code = BIBSTYLE_RE.sub(style_replacement, code)
        rewritten_lines.append(code + comment)
    return "".join(rewritten_lines), dependencies


def collect_and_copy_sources(root: Path, destination: Path) -> list[Path]:
    """Copy and rewrite the complete manuscript dependency graph."""

    main = (root / "main.tex").resolve()
    if not main.is_file():
        raise SubmissionBuildError(f"missing manuscript source: {main}")
    queue = [main]
    visited: set[Path] = set()
    emitted: list[Path] = []
    while queue:
        source = queue.pop(0).resolve()
        if source in visited:
            continue
        visited.add(source)
        output = destination / flat_name(source, root, main=main)
        if output.exists():
            raise SubmissionBuildError(f"flat-name collision at {output.name}")
        if source.suffix.lower() == ".tex":
            rewritten, dependencies = _rewrite_tex(source, root=root, main=main)
            output.write_text(rewritten, encoding="utf-8")
            queue.extend(sorted(dependencies, key=lambda item: item.as_posix()))
        else:
            shutil.copy2(source, output)
        emitted.append(output)

    for name in FIXED_ELSEVIER_FILES:
        source = root / name
        if not source.is_file():
            raise SubmissionBuildError(f"missing required Elsevier source: {source}")
        output = destination / name
        if not output.exists():
            shutil.copy2(source, output)
            emitted.append(output)
    references = root / "references.bib"
    if not references.is_file():
        raise SubmissionBuildError(
            "missing required editable bibliography source: references.bib"
        )
    if not (destination / "references.bib").exists():
        shutil.copy2(references, destination / "references.bib")
        emitted.append(destination / "references.bib")
    return emitted


def copy_standard_bibliography_styles(destination: Path) -> list[Path]:
    """Vendor standard ``.bst`` files named by the flattened TeX sources."""

    styles: set[str] = set()
    for tex_path in destination.glob("*.tex"):
        source = "".join(
            _strip_comment(line)[0]
            for line in tex_path.read_text(encoding="utf-8").splitlines(keepends=True)
        )
        styles.update(match.strip() for match in BIBSTYLE_RE.findall(source))
    emitted: list[Path] = []
    for style in sorted(styles):
        name = style if style.endswith(".bst") else f"{style}.bst"
        target = destination / name
        if target.is_file():
            continue
        kpsewhich = shutil.which("kpsewhich")
        if kpsewhich is None:
            raise SubmissionBuildError(
                f"cannot vendor bibliography style {name}: kpsewhich is unavailable"
            )
        completed = subprocess.run(
            [kpsewhich, name], check=False, capture_output=True, text=True
        )
        source_name = completed.stdout.strip()
        source = Path(source_name) if completed.returncode == 0 and source_name else None
        if source is None or not source.is_file():
            raise SubmissionBuildError(f"bibliography style is unavailable: {name}")
        shutil.copy2(source, target)
        emitted.append(target)
    return emitted


def read_highlights(path: Path) -> list[str]:
    """Read Markdown bullets as plain-text submission highlights."""

    if not path.is_file():
        raise SubmissionBuildError(f"missing highlights source: {path}")
    highlights = [
        match.group(1).strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^\s*[-*]\s+(.+?)\s*$", line))
    ]
    if not highlights:
        raise SubmissionBuildError(f"no Markdown bullets found in {path}")
    return highlights


def _copy_author_files(root: Path, current: Path, destination: Path) -> None:
    fallback_names = {
        "cover_letter.tex": ("cover_letter_array.tex", "cover_letter.tex"),
        "README_SUBMISSION.md": ("README_SUBMISSION.md",),
        "submission_checklist.md": ("submission_checklist.md",),
    }
    missing: list[str] = []
    for name in AUTHOR_MAINTAINED:
        candidates = [current / name]
        candidates.extend(root / fallback for fallback in fallback_names[name])
        source = next((candidate for candidate in candidates if candidate.is_file()), None)
        if source is None:
            missing.append(name)
        else:
            shutil.copy2(source, destination / name)
    if missing:
        raise SubmissionBuildError(
            "missing author-maintained submission files: " + ", ".join(missing)
        )


def _run_latexmk(tex_name: str, directory: Path, latexmk: str) -> None:
    try:
        completed = subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_name],
            cwd=directory,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        raise SubmissionBuildError(f"cannot execute {latexmk!r}: {error}") from error
    if completed.returncode:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-80:])
        raise SubmissionBuildError(f"LaTeX compilation failed for {tex_name}:\n{tail}")


def _remove_auxiliary_files(directory: Path) -> None:
    for path in directory.iterdir():
        if path.is_file() and any(path.name.endswith(suffix) for suffix in BUILD_AUXILIARY_SUFFIXES):
            path.unlink()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(directory: Path) -> None:
    files = [path for path in directory.iterdir() if path.is_file() and path.name != "BUILD_MANIFEST.json"]
    manifest = {
        "schema_version": 1,
        "hash_algorithm": "SHA-256",
        "layout": "flat",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(files, key=lambda item: item.name)
        ],
    }
    (directory / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_submission(
    *,
    root: Path = REPOSITORY_ROOT,
    output: Path = DEFAULT_OUTPUT,
    compile_pdf: bool = True,
    latexmk: str = "latexmk",
) -> list[str]:
    """Build the package atomically and return its final filenames."""

    root = root.resolve()
    output = output.resolve()
    if output == root or output in root.parents:
        raise SubmissionBuildError(
            "refusing an output path that is the repository root or one of its parents"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".array-build-", dir=output.parent) as temp_name:
        staging = Path(temp_name)
        _copy_author_files(root, output, staging)
        collect_and_copy_sources(root, staging)
        copy_standard_bibliography_styles(staging)
        highlights = read_highlights(root / "HIGHLIGHTS.md")
        (staging / "highlights.txt").write_text(
            "\n".join(f"- {item}" for item in highlights) + "\n", encoding="utf-8"
        )
        if compile_pdf:
            _run_latexmk("main.tex", staging, latexmk)
            _run_latexmk("cover_letter.tex", staging, latexmk)
            _remove_auxiliary_files(staging)
        _write_manifest(staging)
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    return sorted(path.name for path in output.iterdir() if path.is_file())


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--latexmk", default="latexmk")
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="build sources without PDFs (intended only for unit tests/debugging)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        files = build_submission(
            root=args.root,
            output=args.output,
            compile_pdf=not args.no_compile,
            latexmk=args.latexmk,
        )
    except SubmissionBuildError as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Built flat Array package at {args.output.resolve()} ({len(files)} files)")
    for name in files:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
