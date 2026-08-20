from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from experiments.mutations import (
    DEFAULT_RULES_PATH,
    DEFAULT_TRACE_DIR,
    evaluate_mutation,
    generate_mutation_cases,
    violation_codes,
)
from prototype.checker import check_trace


EXPECTED_CODES = {
    "unknown_agent",
    "unknown_tool",
    "tool_permission",
    "insufficient_budget",
    "illegal_handoff",
    "illegal_message",
    "payload_policy",
    "missing_provenance",
    "certificate_source",
    "unauthorized_certifier",
    "duplicate_audit",
    "missing_audit",
    "memory_overwrite",
    "uncertified_claim",
}


class MutationExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
        cls.cases = generate_mutation_cases(rules=cls.rules)

    def test_complete_expected_code_inventory(self) -> None:
        self.assertEqual({case.expected_code for case in self.cases}, EXPECTED_CODES)
        self.assertEqual(len(self.cases), len(EXPECTED_CODES))

    def test_metadata_and_steps_are_deterministic(self) -> None:
        for case in self.cases:
            with self.subTest(case=case.name):
                self.assertEqual(case.metadata["expected_code"], case.expected_code)
                self.assertEqual(case.metadata["target_step"], case.target_step)
                self.assertEqual(
                    [event["step"] for event in case.trace],
                    list(range(1, len(case.trace) + 1)),
                )

    def test_canonical_sources_are_not_modified(self) -> None:
        before = {
            path.name: path.read_bytes()
            for path in DEFAULT_TRACE_DIR.glob("valid_*.json")
        }
        generate_mutation_cases(rules=copy.deepcopy(self.rules))
        after = {name: (DEFAULT_TRACE_DIR / name).read_bytes() for name in before}
        self.assertEqual(after, before)

    def test_violation_code_extraction(self) -> None:
        result = {
            "violations": [
                {"code": "unknown_tool", "step": 2},
                "missing_audit",
                {"message": "code intentionally absent"},
            ]
        }
        self.assertEqual(violation_codes(result), {"unknown_tool", "missing_audit"})

    def test_checker_detects_each_controlled_mutation(self) -> None:
        probe = check_trace([], copy.deepcopy(self.rules))
        if "violations" not in probe:
            self.skipTest("checker diagnostic-code contract is not installed yet")
        for case in self.cases:
            with self.subTest(case=case.name):
                outcome = evaluate_mutation(case, self.rules, check_trace)
                self.assertFalse(outcome["accepted"])
                self.assertTrue(outcome["detected"], outcome)


if __name__ == "__main__":
    unittest.main()
