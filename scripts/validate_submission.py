#!/usr/bin/env python3
"""Validate objective constraints of the flat Array submission package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPOSITORY_ROOT / "submission" / "array"
REQUIRED_FILES = (
    "main.tex",
    "main.pdf",
    "references.bib",
    "cas-sc.cls",
    "cas-common.sty",
    "highlights.txt",
    "cover_letter.tex",
    "cover_letter.pdf",
    "README_SUBMISSION.md",
    "submission_checklist.md",
    "BUILD_MANIFEST.json",
    "unsrtnat.bst",
)
PROHIBITED_SUFFIXES = {
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
REFERENCE_RE = re.compile(
    r"\\(?:ref|eqref|pageref|autoref|cref|Cref)\s*\{([^{}]+)\}"
)
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
CITATION_RE = re.compile(
    r"\\cite[A-Za-z*]*(?:\s*\[[^]]*\]){0,2}\s*\{([^{}]+)\}"
)
BIBITEM_RE = re.compile(r"\\bibitem(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}")
BIBENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
GRAPHIC_RE = re.compile(r"\\includegraphics(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}")
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{([^{}]+)\}")
BIBSTYLE_RE = re.compile(r"\\bibliographystyle\s*\{([^{}]+)\}")


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str


def _without_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        split_at = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                split_at = index
                break
        lines.append(line[:split_at])
    return "\n".join(lines)


def _extract_environment(text: str, name: str) -> str | None:
    match = re.search(
        rf"\\begin\{{{re.escape(name)}\}}(.*?)\\end\{{{re.escape(name)}\}}",
        text,
        flags=re.DOTALL,
    )
    return match.group(1) if match else None


def _plain_tex(text: str) -> str:
    value = re.sub(r"\$.*?\$", " ", text, flags=re.DOTALL)
    value = re.sub(r"\\\[.*?\\\]", " ", value, flags=re.DOTALL)
    value = re.sub(r"\\begin\{[^{}]+\}.*?\\end\{[^{}]+\}", " ", value, flags=re.DOTALL)
    value = re.sub(r"\\(?:cite\w*|ref|eqref|label|footnote)\s*\{[^{}]*\}", " ", value)
    # Repeated passes unwrap common formatting commands while retaining their text.
    for _ in range(4):
        value = re.sub(r"\\[A-Za-z@]+\*?(?:\s*\[[^]]*\])?\s*\{([^{}]*)\}", r" \1 ", value)
    value = re.sub(r"\\[A-Za-z@]+\*?", " ", value)
    value = value.replace("~", " ").replace("--", " ")
    value = re.sub(r"[{}_^&]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", _plain_tex(text)))


def parse_highlights(path: Path) -> list[str]:
    if not path.is_file():
        return []
    highlights: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        highlights.append(re.sub(r"^[-*]\s+", "", line).strip())
    return highlights


def validate_content(bundle: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    main_path = bundle / "main.tex"
    if not main_path.is_file():
        return [ValidationIssue("ERROR", "missing-main", f"missing {main_path}")]
    tex_paths = sorted(
        path for path in bundle.glob("*.tex") if path.name != "cover_letter.tex"
    )
    corpus = "\n".join(
        _without_comments(path.read_text(encoding="utf-8")) for path in tex_paths
    )
    main = _without_comments(main_path.read_text(encoding="utf-8"))

    abstract = _extract_environment(main, "abstract")
    if abstract is None:
        issues.append(ValidationIssue("ERROR", "abstract-missing", "main.tex has no abstract environment"))
    else:
        count = word_count(abstract)
        if count == 0 or count > 250:
            issues.append(
                ValidationIssue(
                    "ERROR", "abstract-length", f"abstract has {count} words; Array permits at most 250"
                )
            )

    keywords = _extract_environment(main, "keywords")
    if keywords is None:
        issues.append(ValidationIssue("ERROR", "keywords-missing", "main.tex has no keywords environment"))
    else:
        items = [item.strip() for item in re.split(r"\\sep|;", keywords) if item.strip()]
        if not 1 <= len(items) <= 7:
            issues.append(
                ValidationIssue(
                    "ERROR", "keyword-count", f"found {len(items)} keywords; Array requires 1-7"
                )
            )

    highlights = parse_highlights(bundle / "highlights.txt")
    if not 3 <= len(highlights) <= 5:
        issues.append(
            ValidationIssue(
                "ERROR", "highlight-count", f"found {len(highlights)} highlights; Elsevier requires 3-5"
            )
        )
    for index, highlight in enumerate(highlights, start=1):
        if len(highlight) > 85:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "highlight-length",
                    f"highlight {index} has {len(highlight)} characters; maximum is 85",
                )
            )

    labels = LABEL_RE.findall(corpus)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    for label in duplicates:
        issues.append(ValidationIssue("ERROR", "duplicate-label", f"duplicate LaTeX label: {label}"))
    label_set = set(labels)
    references = {key.strip() for group in REFERENCE_RE.findall(corpus) for key in group.split(",")}
    for key in sorted(references - label_set):
        issues.append(ValidationIssue("ERROR", "missing-label", f"reference has no label: {key}"))
    for label in sorted(item for item in label_set if item.startswith(("fig:", "tab:"))):
        if label not in references:
            issues.append(ValidationIssue("ERROR", "uncited-float", f"figure/table label is never cited: {label}"))

    citations = {
        key.strip()
        for group in CITATION_RE.findall(corpus)
        for key in group.split(",")
        if key.strip() and key.strip() != "*"
    }
    bibliography = set(BIBITEM_RE.findall(corpus))
    for bib_path in bundle.glob("*.bib"):
        bibliography.update(BIBENTRY_RE.findall(_without_comments(bib_path.read_text(encoding="utf-8"))))
    for key in sorted(citations - bibliography):
        issues.append(ValidationIssue("ERROR", "missing-citation", f"citation has no bibliography entry: {key}"))
    for key in sorted(bibliography - citations):
        issues.append(ValidationIssue("ERROR", "uncited-bibliography", f"bibliography entry is not cited: {key}"))

    for pattern, suffixes, code in (
        (INPUT_RE, ("", ".tex"), "missing-input"),
        (GRAPHIC_RE, ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps"), "missing-graphic"),
        (BIBLIOGRAPHY_RE, ("", ".bib"), "missing-bibliography"),
        (BIBSTYLE_RE, ("", ".bst"), "missing-bibliography-style"),
    ):
        for group in pattern.findall(corpus):
            for raw in group.split(","):
                reference = raw.strip()
                if "/" in reference or "\\" in reference:
                    issues.append(
                        ValidationIssue("ERROR", "non-flat-reference", f"source reference is not flat: {reference}")
                    )
                    continue
                if not any((bundle / f"{reference}{suffix}").is_file() for suffix in suffixes):
                    issues.append(ValidationIssue("ERROR", code, f"referenced file is absent: {reference}"))

    lower_main = main.lower()
    declaration_terms = {
        "data-availability": "data availability",
        "funding-statement": "funding",
        "competing-interests": "competing interests",
        "credit-statement": "credit authorship",
        "ai-declaration": "generative ai",
    }
    for code, term in declaration_terms.items():
        if term not in lower_main:
            issues.append(ValidationIssue("ERROR", code, f"manuscript is missing a {term} statement"))
    if "jlamp" in lower_main or "journal of logical and algebraic methods" in lower_main:
        issues.append(
            ValidationIssue("ERROR", "stale-journal", "manuscript still contains JLAMP-specific text")
        )

    cover_path = bundle / "cover_letter.tex"
    if cover_path.is_file():
        cover = _without_comments(cover_path.read_text(encoding="utf-8")).lower()
        if "array" not in cover:
            issues.append(ValidationIssue("ERROR", "cover-journal", "cover letter does not name Array"))
        if "regular paper" not in cover:
            issues.append(ValidationIssue("ERROR", "cover-article-type", "cover letter does not identify a Regular Paper"))
        if "jlamp" in cover or "journal of logical and algebraic methods" in cover:
            issues.append(ValidationIssue("ERROR", "cover-stale-journal", "cover letter contains stale JLAMP text"))
    return issues


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_bundle_layout(bundle: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not bundle.is_dir():
        return [ValidationIssue("ERROR", "bundle-missing", f"submission directory does not exist: {bundle}")]
    for name in REQUIRED_FILES:
        path = bundle / name
        if not path.is_file():
            issues.append(ValidationIssue("ERROR", "required-file", f"required submission file is missing: {name}"))
    nested = sorted(path.relative_to(bundle).as_posix() for path in bundle.rglob("*") if path.is_dir())
    for path in nested:
        issues.append(ValidationIssue("ERROR", "non-flat-layout", f"submission contains a directory: {path}"))
    for path in sorted(bundle.iterdir(), key=lambda item: item.name):
        if path.is_symlink():
            issues.append(ValidationIssue("ERROR", "bundle-symlink", f"submission contains a symlink: {path.name}"))
        if path.is_file() and any(path.name.endswith(suffix) for suffix in PROHIBITED_SUFFIXES):
            issues.append(ValidationIssue("ERROR", "build-artifact", f"temporary build file is present: {path.name}"))
    manifest_path = bundle / "BUILD_MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            issues.append(ValidationIssue("ERROR", "bundle-manifest", f"cannot parse BUILD_MANIFEST.json: {error}"))
        else:
            if manifest.get("layout") != "flat" or manifest.get("hash_algorithm") != "SHA-256":
                issues.append(ValidationIssue("ERROR", "bundle-manifest", "invalid bundle manifest metadata"))
            if manifest.get("schema_version") != 1:
                issues.append(ValidationIssue("ERROR", "bundle-manifest", "unsupported bundle manifest schema"))
            entries = manifest.get("files", [])
            if not isinstance(entries, list):
                issues.append(ValidationIssue("ERROR", "bundle-manifest", "bundle manifest files is not a list"))
            else:
                recorded = set()
                for entry in entries:
                    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
                        issues.append(ValidationIssue("ERROR", "bundle-manifest", f"malformed manifest entry: {entry!r}"))
                        continue
                    name = entry["path"]
                    if Path(name).is_absolute() or Path(name).name != name:
                        issues.append(ValidationIssue("ERROR", "bundle-manifest", f"manifest path is not flat: {name}"))
                        continue
                    if name in recorded:
                        issues.append(ValidationIssue("ERROR", "bundle-manifest", f"duplicate manifest path: {name}"))
                    recorded.add(name)
                    candidate = bundle / name
                    if not candidate.is_file():
                        issues.append(ValidationIssue("ERROR", "bundle-manifest", f"manifest file is missing: {name}"))
                    elif candidate.stat().st_size != entry.get("bytes") or _sha256(candidate) != entry.get("sha256"):
                        issues.append(ValidationIssue("ERROR", "bundle-manifest", f"manifest mismatch: {name}"))
                actual = {path.name for path in bundle.iterdir() if path.is_file() and path.name != manifest_path.name}
                for name in sorted(actual - recorded):
                    issues.append(ValidationIssue("ERROR", "bundle-manifest", f"unrecorded bundle file: {name}"))
    return issues


def compile_in_isolation(bundle: Path, latexmk: str = "latexmk") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    with tempfile.TemporaryDirectory(prefix="array-submission-check-") as temp_name:
        isolated = Path(temp_name)
        for source in bundle.iterdir():
            if source.is_file():
                shutil.copy2(source, isolated / source.name)
        for tex_name in ("main.tex", "cover_letter.tex"):
            if not (isolated / tex_name).is_file():
                continue
            try:
                completed = subprocess.run(
                    [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_name],
                    cwd=isolated,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError as error:
                issues.append(ValidationIssue("ERROR", "latex-unavailable", f"cannot execute {latexmk!r}: {error}"))
                return issues
            combined = completed.stdout + "\n" + completed.stderr
            log_path = isolated / f"{Path(tex_name).stem}.log"
            if log_path.is_file():
                combined += "\n" + log_path.read_text(encoding="utf-8", errors="replace")
            if completed.returncode:
                tail = " | ".join(combined.splitlines()[-25:])
                issues.append(ValidationIssue("ERROR", "latex-compile", f"isolated compilation failed for {tex_name}: {tail}"))
                continue
            pdf = isolated / f"{Path(tex_name).stem}.pdf"
            if not pdf.is_file() or pdf.stat().st_size < 1024:
                issues.append(ValidationIssue("ERROR", "pdf-output", f"compilation did not produce a nonempty {pdf.name}"))
            warning_patterns = {
                "undefined-reference": r"(?:Reference .* undefined|There were undefined references)",
                "undefined-citation": r"(?:Citation .* undefined|There were undefined citations)",
                "missing-file": r"LaTeX Error: File `[^']+' not found",
            }
            for code, pattern in warning_patterns.items():
                if re.search(pattern, combined, flags=re.IGNORECASE):
                    issues.append(ValidationIssue("ERROR", code, f"{tex_name} log contains {code.replace('-', ' ')}"))
    return issues


def validate_experiment_manifest(root: Path) -> list[ValidationIssue]:
    manifest = root / "experiments" / "results" / "MANIFEST.json"
    if not manifest.is_file():
        return [ValidationIssue("ERROR", "experiment-manifest", f"missing experiment manifest: {manifest}")]
    completed = subprocess.run(
        [sys.executable, "-m", "experiments.run_all", "--verify"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = " | ".join((completed.stdout + completed.stderr).splitlines()[-20:])
        return [ValidationIssue("ERROR", "experiment-manifest", f"experiment artifacts are stale: {detail}")]
    return []


def validate_submission(
    *,
    bundle: Path = DEFAULT_BUNDLE,
    root: Path = REPOSITORY_ROOT,
    compile_pdf: bool = True,
    verify_experiments: bool = True,
    latexmk: str = "latexmk",
) -> list[ValidationIssue]:
    bundle = bundle.resolve()
    issues = validate_bundle_layout(bundle)
    if bundle.is_dir() and (bundle / "main.tex").is_file():
        issues.extend(validate_content(bundle))
        if compile_pdf:
            issues.extend(compile_in_isolation(bundle, latexmk))
    if verify_experiments:
        issues.extend(validate_experiment_manifest(root.resolve()))
    return issues


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--latexmk", default="latexmk")
    parser.add_argument("--skip-compile", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--json-report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    issues = validate_submission(
        bundle=args.bundle,
        root=args.root,
        compile_pdf=not args.skip_compile,
        verify_experiments=not args.skip_manifest,
        latexmk=args.latexmk,
    )
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps([asdict(issue) for issue in issues], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    errors = [issue for issue in issues if issue.severity == "ERROR"]
    for issue in issues:
        print(f"{issue.severity} [{issue.code}] {issue.message}")
    if errors:
        print(f"Submission validation failed: {len(errors)} error(s).")
        return 1
    print("Submission validation passed: package is flat, complete, and independently compilable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
