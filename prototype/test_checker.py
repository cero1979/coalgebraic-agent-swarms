from __future__ import annotations

import json
import unittest
from pathlib import Path

from checker import check_trace


ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "prototype/rules.json").read_text(encoding="utf-8"))


class CheckerConformanceTests(unittest.TestCase):
    def test_all_named_conformance_traces(self) -> None:
        trace_dir = ROOT / "prototype/traces"
        for path in sorted(trace_dir.glob("*.json")):
            with self.subTest(trace=path.name):
                trace = json.loads(path.read_text(encoding="utf-8"))
                result = check_trace(trace, RULES)
                self.assertEqual(result["accepted"], path.name.startswith("valid_"))

    def test_rejected_event_does_not_commit_ledger_effects(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "tool_call",
                "agent": "Planner",
                "tool": "BibliographicSearch",
                "trace": "tr-invalid-permission",
                "writes": [
                    {"scope": "shared", "key": "should_not_exist", "value": "x"}
                ],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["final_budgets"], RULES["initial_budgets"])
        self.assertEqual(result["shared_memory"], [])
        self.assertEqual(result["counters"]["budget_consumed"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)


if __name__ == "__main__":
    unittest.main()
