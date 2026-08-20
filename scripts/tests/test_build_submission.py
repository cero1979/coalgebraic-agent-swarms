from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_submission import SubmissionBuildError, _run_latexmk, build_submission


class BuildSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.output = self.root / "submission" / "array"
        (self.root / "paper" / "generated").mkdir(parents=True)
        (self.root / "paper" / "figures").mkdir(parents=True)
        self.output.mkdir(parents=True)
        (self.root / "cas-sc.cls").write_text("% class\n", encoding="utf-8")
        (self.root / "cas-common.sty").write_text("% style\n", encoding="utf-8")
        (self.root / "HIGHLIGHTS.md").write_text(
            "# Highlights\n\n- First result.\n- Second result.\n- Third result.\n",
            encoding="utf-8",
        )
        (self.root / "references.bib").write_text(
            "@article{example, title={Example}}\n", encoding="utf-8"
        )
        (self.root / "unsrtnat.bst").write_text("% bst\n", encoding="utf-8")
        (self.root / "paper" / "generated" / "table.tex").write_text(
            "\\begin{tabular}{c}ok\\end{tabular}\n", encoding="utf-8"
        )
        (self.root / "paper" / "figures" / "plot.pdf").write_bytes(b"%PDF-fixture")
        (self.root / "main.tex").write_text(
            "\\documentclass{cas-sc}\n"
            "% \\input{missing-commented-file}\n"
            "\\begin{document}\n"
            "\\input{paper/generated/table}\n"
            "\\includegraphics{paper/figures/plot.pdf}\n"
            "\\bibliographystyle{unsrtnat}\n"
            "\\bibliography{references}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        for name, content in (
            ("cover_letter.tex", "\\documentclass{article}\\begin{document}Cover\\end{document}\n"),
            ("README_SUBMISSION.md", "# Submission\n"),
            ("submission_checklist.md", "# Checklist\n"),
        ):
            (self.output / name).write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_build_is_flat_and_rewrites_nested_dependencies(self) -> None:
        (self.output / "stale.abs").write_text("generated\n", encoding="utf-8")
        names = build_submission(
            root=self.root,
            output=self.output,
            compile_pdf=False,
        )
        self.assertIn("paper__generated__table.tex", names)
        self.assertIn("paper__figures__plot.pdf", names)
        self.assertIn("references.bib", names)
        self.assertFalse(any(path.is_dir() for path in self.output.iterdir()))
        rewritten = (self.output / "main.tex").read_text(encoding="utf-8")
        self.assertIn(r"\input{paper__generated__table.tex}", rewritten)
        self.assertIn(r"\includegraphics{paper__figures__plot.pdf}", rewritten)
        self.assertIn(r"\bibliography{references}", rewritten)
        self.assertIn("unsrtnat.bst", names)
        self.assertIn(r"% \input{missing-commented-file}", rewritten)
        self.assertTrue((self.output / "BUILD_MANIFEST.json").is_file())
        self.assertFalse((self.output / "stale.abs").exists())

    def test_author_files_are_required_and_existing_files_survive_rebuild(self) -> None:
        cover = self.output / "cover_letter.tex"
        expected = cover.read_text(encoding="utf-8")
        build_submission(root=self.root, output=self.output, compile_pdf=False)
        self.assertEqual(expected, (self.output / "cover_letter.tex").read_text(encoding="utf-8"))

        (self.output / "README_SUBMISSION.md").unlink()
        with self.assertRaisesRegex(SubmissionBuildError, "README_SUBMISSION.md"):
            build_submission(root=self.root, output=self.output, compile_pdf=False)

    def test_missing_live_dependency_is_an_error(self) -> None:
        with (self.root / "main.tex").open("a", encoding="utf-8") as handle:
            handle.write("\\input{missing-live-file}\n")
        with self.assertRaisesRegex(SubmissionBuildError, "missing dependency"):
            build_submission(root=self.root, output=self.output, compile_pdf=False)

    def test_repository_root_cannot_be_used_as_output(self) -> None:
        with self.assertRaisesRegex(SubmissionBuildError, "refusing an output path"):
            build_submission(root=self.root, output=self.root, compile_pdf=False)

    @patch("scripts.build_submission.subprocess.run")
    def test_latex_output_tolerates_non_utf8_bytes(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "compiler output with replacement: \ufffd"
        run.return_value.stderr = ""

        _run_latexmk("main.tex", self.root, "latexmk")

        self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
        self.assertEqual("replace", run.call_args.kwargs["errors"])


if __name__ == "__main__":
    unittest.main()
