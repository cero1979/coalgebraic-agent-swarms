from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.run_all import (
    RESULT_FILENAMES,
    TABLE_FILENAMES,
    _parse_args,
    execute_all,
    execute_selected,
    run_e2,
    run_e3,
    verify_manifest,
)
from prototype.checker import load_json


ROOT = Path(__file__).resolve().parents[2]
RULES = load_json(ROOT / "prototype" / "rules.json")


class FrameworkMutationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.framework_runs = run_e2(RULES)
        cls.mutations = run_e3(cls.framework_runs, RULES)

    def test_three_real_framework_runs_are_accepted(self) -> None:
        self.assertEqual(len(self.framework_runs), 3)
        self.assertEqual(
            {item["workflow"] for item in self.framework_runs},
            {"research", "resource_controlled", "shared_memory"},
        )
        self.assertTrue(all(item["checker_result"]["accepted"] for item in self.framework_runs))
        self.assertTrue(all(item["native_stream"] for item in self.framework_runs))
        self.assertTrue(all(item["canonical_trace"] for item in self.framework_runs))

    def test_each_framework_trace_supplies_fourteen_exact_mutations(self) -> None:
        self.assertEqual(len(self.mutations), 42)
        for workflow in {item["workflow"] for item in self.framework_runs}:
            cases = [item for item in self.mutations if item["workflow"] == workflow]
            self.assertEqual(len(cases), 14)
            self.assertTrue(all(item["strictly_detected"] for item in cases))
            self.assertTrue(
                all(item["canonical_trace"].startswith(f"{workflow}:") for item in cases)
            )


class CompleteRunnerTests(unittest.TestCase):
    def test_default_cli_selection_is_the_complete_evaluation(self) -> None:
        args = _parse_args([])
        self.assertEqual(args.only, "all")
        self.assertFalse(args.verify)

    def test_full_run_emits_and_verifies_the_complete_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            generated = root / "generated"
            report = execute_all(
                results_dir=results,
                generated_dir=generated,
                lengths=(10,),
                repetitions=1,
                warmups=0,
            )
            summary = report["summary"]
            self.assertEqual(summary["E1_conformance"]["expectation_matches"], 19)
            self.assertEqual(summary["E2_framework_validation"]["accepted"], 3)
            self.assertEqual(summary["E3_mutation_testing"]["strictly_detected"], 42)
            self.assertEqual(summary["E4_scaling"]["lengths"], [10])
            self.assertEqual(
                {path.name for path in results.iterdir()},
                {*RESULT_FILENAMES, "MANIFEST.json"},
            )
            self.assertEqual(
                {path.name for path in generated.iterdir()}, set(TABLE_FILENAMES)
            )
            self.assertEqual(
                verify_manifest(
                    results / "MANIFEST.json",
                    results_dir=results,
                    generated_dir=generated,
                ),
                [],
            )

            summary_path = results / "summary.json"
            document = json.loads(summary_path.read_text(encoding="utf-8"))
            document["schema_version"] = 999
            summary_path.write_text(json.dumps(document), encoding="utf-8")
            errors = verify_manifest(
                results / "MANIFEST.json",
                results_dir=results,
                generated_dir=generated,
            )
            self.assertTrue(any("SHA-256 mismatch" in error for error in errors))
            self.assertTrue(any("summary.json does not match" in error for error in errors))

    def test_partial_run_removes_a_stale_full_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = root / "results"
            generated = root / "generated"
            execute_all(
                results_dir=results,
                generated_dir=generated,
                lengths=(10,),
                repetitions=1,
                warmups=0,
            )
            self.assertTrue((results / "MANIFEST.json").is_file())
            report = execute_selected(
                "conformance", results_dir=results, generated_dir=generated
            )
            self.assertTrue(report["manifest_removed"])
            self.assertFalse((results / "MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
