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
import zipfile
from pathlib import Path
from typing import Iterable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "submission" / "array"
DEFAULT_UPLOAD_OUTPUT = REPOSITORY_ROOT / "output" / "submission"
AUTHOR_MAINTAINED = (
    "cover_letter.tex",
    "title_page.tex",
    "title_page.docx",
    "README_SUBMISSION.md",
    "submission_checklist.md",
)
FIXED_ELSEVIER_FILES = ("cas-sc.cls", "cas-common.sty")
GRAPHIC_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
MANUSCRIPT_SOURCE_SUFFIXES = {".tex", ".bib", ".bst", ".cls", ".sty"}
BUILD_AUXILIARY_SUFFIXES = {
    ".abs",
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

ANONYMOUS_MAIN_REPLACEMENTS = {
    "author-metadata": (
        "\\shortauthors{Anonymous}\n"
        "\\author[]{Anonymous author(s)}\n"
    ),
    "reproducibility-release": (
        "The exact software and original synthetic data snapshot accompanying "
        "this revised manuscript is supplied in the separately uploaded "
        "anonymous replication archive~\\cite{artifact2026,artifactdata2026}. "
        "It contains source code, traces, generated results, and SHA-256 "
        "manifests. No archival DOI or public mirror for this revision is "
        "claimed during peer review.\n"
    ),
    "credit-statement": (
        "\\section*{CRediT authorship contribution statement}\n"
        "Contributor-role details are supplied in the separate title page and "
        "are withheld from this manuscript copy for anonymous review.\n"
    ),
    "data-availability": (
        "\\section*{Data and code availability}\n"
        "All research data reported in this article are original synthetic data "
        "generated for the study. The conformance traces, framework-derived "
        "records, mutation cases, scaling observations, source code, and integrity "
        "manifests are supplied in the separately uploaded anonymous "
        "supplementary archive for peer review. No reference or third-party "
        "dataset was analysed.\n"
    ),
}

ANONYMOUS_BIBLIOGRAPHY_REPLACEMENTS = {
    "artifact-software": (
        "@misc{artifact2026,\n"
        "  author       = {{Anonymous}},\n"
        "  title        = {Anonymous Software Artifact Accompanying This Submission},\n"
        "  year         = {2026},\n"
        "  howpublished = {Supplementary archive supplied with this submission},\n"
        "  note         = {Version-matched software for anonymous peer review}\n"
        "}\n"
    ),
    "artifact-data": (
        "@misc{artifactdata2026,\n"
        "  author       = {{Anonymous}},\n"
        "  title        = {{[dataset]} Anonymous Synthetic Validation Data Accompanying This Submission},\n"
        "  year         = {2026},\n"
        "  howpublished = {Dataset in supplementary archive supplied with this submission},\n"
        "  note         = {Version-matched original synthetic data for anonymous peer review}\n"
        "}\n"
    ),
}


class SubmissionBuildError(RuntimeError):
    """Raised when a complete, unambiguous source bundle cannot be built."""


def _replace_marked_sections(
    text: str,
    replacements: dict[str, str],
    *,
    source_name: str,
) -> str:
    """Replace explicitly marked identity-bearing sections exactly once."""

    rewritten = text
    for name, replacement in replacements.items():
        start = f"% ARRAY-ANON-BEGIN {name}"
        end = f"% ARRAY-ANON-END {name}"
        if rewritten.count(start) != 1 or rewritten.count(end) != 1:
            raise SubmissionBuildError(
                f"expected one anonymous-review marker pair {name!r} in {source_name}"
            )
        before, remainder = rewritten.split(start, 1)
        _, after = remainder.split(end, 1)
        rewritten = before + replacement.rstrip() + after
    return rewritten


def _anonymize_main(text: str) -> str:
    rewritten = _replace_marked_sections(
        text,
        ANONYMOUS_MAIN_REPLACEMENTS,
        source_name="main.tex",
    )
    documentclass = re.compile(r"\\documentclass\[(?P<options>[^]]*)\]\{cas-sc\}")
    match = documentclass.search(rewritten)
    if match is None:
        raise SubmissionBuildError("main.tex does not use the expected cas-sc document class")
    options = [item.strip() for item in match.group("options").split(",") if item.strip()]
    if "doubleblind" not in options:
        options.append("doubleblind")
    rewritten = documentclass.sub(
        rf"\\documentclass[{','.join(options)}]{{cas-sc}}",
        rewritten,
        count=1,
    )
    rewritten = rewritten.replace(
        "\\hypersetup{allcolors=black,colorlinks=true,hypertexnames=false}",
        "\\hypersetup{allcolors=black,colorlinks=true,hypertexnames=false,pdfauthor={}}",
        1,
    )
    return rewritten


def _anonymize_bibliography(text: str) -> str:
    return _replace_marked_sections(
        text,
        ANONYMOUS_BIBLIOGRAPHY_REPLACEMENTS,
        source_name="references.bib",
    )


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
            if source == main:
                rewritten = _anonymize_main(rewritten)
            output.write_text(rewritten, encoding="utf-8")
            queue.extend(sorted(dependencies, key=lambda item: item.as_posix()))
        elif source == (root / "references.bib").resolve():
            output.write_text(
                _anonymize_bibliography(source.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
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
        "title_page.tex": ("title_page.tex",),
        "title_page.docx": ("title_page.docx",),
        "README_SUBMISSION.md": ("README_SUBMISSION.md",),
        "submission_checklist.md": ("submission_checklist.md",),
    }
    missing: list[str] = []
    for name in AUTHOR_MAINTAINED:
        if name in {"title_page.tex", "title_page.docx"}:
            candidates = [root / name, current / name]
        else:
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


def _write_prototype_manifest(root: Path) -> None:
    entries = {}
    for path in sorted((root / "prototype").rglob("*"), key=lambda item: item.as_posix()):
        if (
            not path.is_file()
            or path.name == "MANIFEST.json"
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        entries[path.relative_to(root).as_posix()] = _sha256(path)
    (root / "prototype" / "results" / "MANIFEST.json").write_text(
        json.dumps({"sha256": entries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _refresh_experiment_manifest(root: Path) -> None:
    manifest_path = root / "experiments" / "results" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for group in ("source_inputs", "generated_artifacts"):
        for entry in manifest[group]:
            path = root / entry["path"]
            if not path.is_file():
                raise SubmissionBuildError(
                    f"anonymous supplement is missing manifest file: {entry['path']}"
                )
            entry["bytes"] = path.stat().st_size
            entry["sha256"] = _sha256(path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_anonymous_supplement(root: Path, destination: Path) -> None:
    """Create reviewer-facing code/data without author or repository identifiers."""

    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="array-anonymous-supplement-") as temp_name:
        staging = Path(temp_name)
        ignored = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store")
        for directory in ("prototype", "integrations", "experiments", "paper"):
            source = root / directory
            if not source.is_dir():
                raise SubmissionBuildError(f"missing supplement source directory: {source}")
            if directory == "paper":
                (staging / "paper").mkdir()
                shutil.copytree(source / "generated", staging / "paper" / "generated", ignore=ignored)
            else:
                shutil.copytree(source, staging / directory, ignore=ignored)
        shutil.copy2(root / "requirements.txt", staging / "requirements.txt")

        environment_path = staging / "experiments" / "results" / "environment.json"
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
        environment["repository_branch"] = "withheld-for-anonymous-review"
        environment["repository_commit"] = "withheld-for-anonymous-review"
        environment_path.write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        (staging / "LICENSE_REVIEW.txt").write_text(
            "MIT License\n\n"
            "Copyright (c) 2026 Anonymous Authors\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
            "of this software and associated documentation files (the \"Software\"), to deal\n"
            "in the Software without restriction, including without limitation the rights\n"
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies\n"
            "of the Software, subject to inclusion of this notice.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n",
            encoding="utf-8",
        )
        (staging / "DATA_LICENSE_REVIEW.txt").write_text(
            "The original synthetic data under prototype/, experiments/results/, and\n"
            "paper/generated/ are provided under CC BY 4.0 by Anonymous Authors for\n"
            "peer review. Public attribution metadata will be restored after review.\n"
            "https://creativecommons.org/licenses/by/4.0/legalcode\n",
            encoding="utf-8",
        )
        (staging / "README_REVIEW.txt").write_text(
            "ANONYMOUS REPLICATION PACKAGE\n\n"
            "This archive contains the checker, 19 conformance traces, three deterministic\n"
            "LangGraph workflows, E1-E4 experiment code and outputs, generated tables, and\n"
            "integrity manifests. It uses no LLM, API key, or commercial service.\n\n"
            "Setup:\n"
            "  python3.12 -m venv .venv\n"
            "  . .venv/bin/activate\n"
            "  python -m pip install -r requirements.txt\n\n"
            "Checks:\n"
            "  python -m unittest discover -s prototype -p 'test*.py'\n"
            "  python -m unittest discover -s integrations/langgraph/tests -p 'test*.py'\n"
            "  python -m unittest discover -s experiments/tests -p 'test*.py'\n"
            "  python prototype/verify_manifest.py prototype/results/MANIFEST.json\n"
            "  python -m experiments.run_all --verify\n",
            encoding="utf-8",
        )
        _write_prototype_manifest(staging)
        _refresh_experiment_manifest(staging)

        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path in sorted(staging.rglob("*"), key=lambda item: item.as_posix()):
                if path.is_file():
                    handle.write(path, arcname=path.relative_to(staging).as_posix())
            handle.comment = b""


def build_editorial_uploads(
    bundle: Path,
    output: Path,
    *,
    supplement_root: Path | None = None,
) -> list[str]:
    """Create clearly separated, flat files for Editorial Manager upload."""

    bundle = bundle.resolve()
    output = output.resolve()
    if not bundle.is_dir():
        raise SubmissionBuildError(f"submission bundle does not exist: {bundle}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".array-uploads-", dir=output.parent) as temp_name:
        staging = Path(temp_name)
        source_files = sorted(
            (
                path
                for path in bundle.iterdir()
                if path.is_file()
                and path.suffix.lower() in MANUSCRIPT_SOURCE_SUFFIXES
                and path.name not in {"cover_letter.tex", "title_page.tex"}
            ),
            key=lambda item: item.name,
        )
        if not source_files or not any(path.name == "main.tex" for path in source_files):
            raise SubmissionBuildError("anonymous manuscript sources are incomplete")
        archive = staging / "array-manuscript-source.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for source in source_files:
                handle.write(source, arcname=source.name)
        with zipfile.ZipFile(archive) as handle:
            names = handle.namelist()
        if any(Path(name).name != name or "/" in name or "\\" in name for name in names):
            raise SubmissionBuildError("Editorial Manager source archive is not flat")

        copies = {
            "main.pdf": "array-manuscript-anonymous.pdf",
            "title_page.tex": "array-title-page.tex",
            "title_page.docx": "array-title-page.docx",
            "title_page.pdf": "array-title-page.pdf",
            "cover_letter.pdf": "array-cover-letter.pdf",
            "highlights.txt": "array-highlights.txt",
        }
        for source_name, output_name in copies.items():
            source = bundle / source_name
            if not source.is_file():
                raise SubmissionBuildError(f"missing Editorial Manager file: {source_name}")
            shutil.copy2(source, staging / output_name)
        if supplement_root is not None:
            _build_anonymous_supplement(
                supplement_root,
                staging / "array-anonymous-supplement.zip",
            )

        instructions = (
            "ARRAY EDITORIAL MANAGER UPLOAD MAP\n\n"
            "Manuscript / LaTeX source files:\n"
            "  array-manuscript-source.zip\n"
            "  This ZIP is flat and contains the anonymous editable manuscript sources.\n\n"
            "Manuscript PDF, only if the current portal stage accepts PDF:\n"
            "  array-manuscript-anonymous.pdf\n\n"
            "Title Page (identified; upload separately, never as manuscript source):\n"
            "  array-title-page.docx is the preferred editable Word file.\n"
            "  array-title-page.tex\n"
            "  array-title-page.pdf is a visual preview.\n\n"
            "Cover Letter:\n"
            "  array-cover-letter.pdf\n\n"
            "Anonymous supplementary software and synthetic data:\n"
            "  array-anonymous-supplement.zip\n\n"
            "No public anonymous repository URL is included until a verified,\n"
            "identity-free mirror of this exact revision is available. The\n"
            "anonymous supplementary archive is the version-matched artifact.\n\n"
            "Highlights:\n"
            "  array-highlights.txt\n\n"
            "Do not upload the entire submission/array directory as one manuscript item.\n"
        )
        (staging / "UPLOAD_INSTRUCTIONS.txt").write_text(instructions, encoding="utf-8")
        checksum_targets = sorted(
            path for path in staging.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt"
        )
        (staging / "SHA256SUMS.txt").write_text(
            "".join(f"{_sha256(path)}  {path.name}\n" for path in checksum_targets),
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    return sorted(path.name for path in output.iterdir() if path.is_file())


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
            _run_latexmk("title_page.tex", staging, latexmk)
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
    parser.add_argument("--upload-output", type=Path, default=DEFAULT_UPLOAD_OUTPUT)
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
        uploads = []
        if not args.no_compile:
            uploads = build_editorial_uploads(
                args.output,
                args.upload_output,
                supplement_root=args.root,
            )
    except SubmissionBuildError as error:
        print(f"ERROR: {error}")
        return 1
    print(f"Built flat Array package at {args.output.resolve()} ({len(files)} files)")
    for name in files:
        print(f"  {name}")
    if uploads:
        print(f"Built Editorial Manager uploads at {args.upload_output.resolve()} ({len(uploads)} files)")
        for name in uploads:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
