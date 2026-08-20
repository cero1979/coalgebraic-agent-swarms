from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.validate_submission import (
    compile_in_isolation,
    parse_highlights,
    main as validation_main,
    validate_bundle_layout,
    validate_content,
    word_count,
)


class ValidateSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.bundle = Path(self.temporary.name) / "array"
        self.bundle.mkdir()
        main = r"""
\documentclass{cas-sc}
\begin{document}
\begin{abstract}
This concise abstract reports a deterministic executable validation study.
\end{abstract}
\begin{keywords}formal methods \sep agent systems\end{keywords}
\section{Method}
See Figure~\ref{fig:pipeline} and cite the artifact~\cite{artifact}.
\begin{figure}\caption{Pipeline}\label{fig:pipeline}\end{figure}
\section*{CRediT authorship contribution statement} All roles were performed by the author.
\section*{Declaration of competing interests} None.
\section*{Funding} No specific grant.
\section*{Data availability} All synthetic traces and software are archived.
\section*{Declaration of generative AI} The author reviewed all outputs.
\bibliographystyle{unsrtnat}
\bibliography{references}
\end{document}
"""
        (self.bundle / "main.tex").write_text(main, encoding="utf-8")
        (self.bundle / "references.bib").write_text(
            "@software{artifact, title={Artifact}}\n", encoding="utf-8"
        )
        (self.bundle / "highlights.txt").write_text(
            "- First concise highlight.\n- Second concise highlight.\n- Third concise highlight.\n",
            encoding="utf-8",
        )
        dummy_files = {
            "main.pdf": b"pdf",
            "cas-sc.cls": b"class",
            "cas-common.sty": b"style",
            "cover_letter.tex": b"Array Regular Paper cover letter",
            "cover_letter.pdf": b"pdf",
            "README_SUBMISSION.md": b"readme",
            "submission_checklist.md": b"checklist",
            "unsrtnat.bst": b"bst",
        }
        for name, content in dummy_files.items():
            (self.bundle / name).write_bytes(content)
        self._write_manifest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_manifest(self) -> None:
        entries = []
        for path in sorted(self.bundle.iterdir(), key=lambda item: item.name):
            if not path.is_file() or path.name == "BUILD_MANIFEST.json":
                continue
            entries.append(
                {
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        (self.bundle / "BUILD_MANIFEST.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "hash_algorithm": "SHA-256",
                    "layout": "flat",
                    "files": entries,
                }
            ),
            encoding="utf-8",
        )

    def test_valid_fixture_passes_content_and_layout_checks(self) -> None:
        self.assertEqual([], validate_content(self.bundle))
        self.assertEqual([], validate_bundle_layout(self.bundle))
        self.assertEqual(3, len(parse_highlights(self.bundle / "highlights.txt")))

    def test_editorial_limits_and_cross_references_are_enforced(self) -> None:
        (self.bundle / "highlights.txt").write_text(
            "- " + "x" * 86 + "\n- only two\n", encoding="utf-8"
        )
        main_path = self.bundle / "main.tex"
        main_path.write_text(
            main_path.read_text(encoding="utf-8").replace(
                r"\ref{fig:pipeline}", r"\ref{fig:missing}"
            ),
            encoding="utf-8",
        )
        codes = {issue.code for issue in validate_content(self.bundle)}
        self.assertIn("highlight-count", codes)
        self.assertIn("highlight-length", codes)
        self.assertIn("missing-label", codes)
        self.assertIn("uncited-float", codes)

    def test_manifest_detects_tampering_and_nested_layout(self) -> None:
        (self.bundle / "main.pdf").write_bytes(b"changed")
        (self.bundle / "main.abs").write_text("generated\n", encoding="utf-8")
        (self.bundle / "nested").mkdir()
        codes = {issue.code for issue in validate_bundle_layout(self.bundle)}
        self.assertIn("build-artifact", codes)
        self.assertIn("bundle-manifest", codes)
        self.assertIn("non-flat-layout", codes)

    def test_tex_word_count_ignores_commands_and_math(self) -> None:
        self.assertEqual(4, word_count(r"A \emph{small} test with $x+y$."))

    def test_cli_exit_status_reflects_objective_validation(self) -> None:
        with redirect_stdout(io.StringIO()):
            valid_status = validation_main(
                ["--bundle", str(self.bundle), "--skip-compile", "--skip-manifest"]
            )
            invalid_status = validation_main(
                [
                    "--bundle",
                    str(self.bundle / "does-not-exist"),
                    "--skip-compile",
                    "--skip-manifest",
                ]
            )
        self.assertEqual(0, valid_status)
        self.assertEqual(1, invalid_status)

    @patch("scripts.validate_submission.subprocess.run")
    def test_isolated_compile_tolerates_non_utf8_output(self, run) -> None:
        def fake_compile(arguments, **kwargs):
            directory = Path(kwargs["cwd"])
            stem = Path(arguments[-1]).stem
            (directory / f"{stem}.pdf").write_bytes(b"x" * 2048)
            (directory / f"{stem}.log").write_text(
                "Final pass has no unresolved references.\n", encoding="utf-8"
            )
            return SimpleNamespace(
                returncode=0,
                stdout="transient first pass: There were undefined references. \ufffd",
                stderr="",
            )

        run.side_effect = fake_compile

        issues = compile_in_isolation(self.bundle)

        self.assertTrue(run.called)
        self.assertNotIn("undefined-reference", {issue.code for issue in issues})
        for call in run.call_args_list:
            self.assertEqual("utf-8", call.kwargs["encoding"])
            self.assertEqual("replace", call.kwargs["errors"])


if __name__ == "__main__":
    unittest.main()
