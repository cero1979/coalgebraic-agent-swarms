from __future__ import annotations

import json
import unittest
from importlib.metadata import version
from pathlib import Path

from integrations.langgraph import (
    AdapterError,
    PINNED_LANGGRAPH_VERSION,
    available_workflows,
    normalize_stream,
    run_workflow,
)
from prototype.checker import check_trace


ROOT = Path(__file__).resolve().parents[3]
RULES = json.loads((ROOT / "prototype/rules.json").read_text(encoding="utf-8"))


class LangGraphIntegrationTests(unittest.TestCase):
    def test_dependency_is_exactly_pinned_version(self) -> None:
        self.assertEqual(version("langgraph"), PINNED_LANGGRAPH_VERSION)
        requirement = (ROOT / "integrations/langgraph/requirements.txt").read_text(
            encoding="utf-8"
        )
        self.assertEqual(requirement.strip(), f"langgraph=={PINNED_LANGGRAPH_VERSION}")

    def test_all_workflows_execute_real_v2_streams_and_pass_checker(self) -> None:
        self.assertEqual(
            available_workflows(),
            ("research", "resource_controlled", "shared_memory"),
        )
        for name in available_workflows():
            with self.subTest(workflow=name):
                result = run_workflow(name, f"test-{name}")
                json.dumps(result["native_stream"])
                record_types = {record["type"] for record in result["native_stream"]}
                self.assertTrue({"tasks", "updates", "values"}.issubset(record_types))
                started_nodes = {
                    record["data"]["name"]
                    for record in result["native_stream"]
                    if record["type"] == "tasks" and "input" in record["data"]
                }
                self.assertGreaterEqual(len(started_nodes), 4)
                trace = result["canonical_trace"]
                self.assertEqual(
                    [event["step"] for event in trace], list(range(1, len(trace) + 1))
                )
                self.assertEqual(len({event["trace"] for event in trace}), len(trace))
                checked = check_trace(trace, RULES)
                self.assertTrue(checked["accepted"], checked["errors"])

    def test_every_native_and_canonical_write_has_explicit_provenance(self) -> None:
        for name in available_workflows():
            result = run_workflow(name, f"provenance-{name}")
            native_writes = []
            for record in result["native_stream"]:
                if record["type"] != "updates":
                    continue
                for update in record["data"].values():
                    for emission in update.get("emissions", []):
                        native_writes.extend(emission.get("writes", []))
            self.assertTrue(native_writes)
            self.assertTrue(all(write.get("provenance") for write in native_writes))
            canonical_writes = [
                write
                for event in result["canonical_trace"]
                for write in event.get("writes", [])
            ]
            self.assertTrue(canonical_writes)
            self.assertTrue(all(write.get("provenance") for write in canonical_writes))
            self.assertTrue(
                all(write["provenance"]["trace"] for write in canonical_writes)
            )

    def test_workflow_specific_paths_are_exercised(self) -> None:
        resource = run_workflow("resource_controlled", "resource-path")
        search_calls = [
            event
            for event in resource["canonical_trace"]
            if event["event"] == "tool_call"
            and event["tool"] == "BibliographicSearch"
        ]
        self.assertEqual(len(search_calls), 2)
        self.assertEqual(resource["final_state"]["remaining_budgets"]["Retriever"], 1)
        resource_nodes = {
            record["data"]["name"]
            for record in resource["native_stream"]
            if record["type"] == "tasks" and "input" in record["data"]
        }
        self.assertIn("resource_budget_gate", resource_nodes)
        self.assertIn("resource_search_secondary", resource_nodes)

        shared = run_workflow("shared_memory", "memory-path")
        memory_writes = [
            write
            for event in shared["canonical_trace"]
            for write in event.get("writes", [])
        ]
        derived = next(write for write in memory_writes if write["key"] == "src_shared_verified")
        self.assertEqual(derived["provenance"]["derived_from"], ["src_shared_raw"])
        self.assertIn("src_shared_raw", shared["final_state"]["shared_memory"])
        self.assertIn("src_shared_verified", shared["final_state"]["shared_memory"])

    def test_adapter_rejects_write_without_provenance(self) -> None:
        native_stream = [
            {
                "type": "updates",
                "ns": [],
                "data": {
                    "retriever": {
                        "emissions": [
                            {
                                "kind": "tool_invocation",
                                "event_id": "bad-write",
                                "actor": "Retriever",
                                "operation": "BibliographicSearch",
                                "inputs": {"query": "q"},
                                "writes": [
                                    {
                                        "namespace": "shared",
                                        "address": "source",
                                        "content": "value",
                                        "provenance": {},
                                    }
                                ],
                            }
                        ]
                    }
                },
            }
        ]
        with self.assertRaisesRegex(AdapterError, "explicit non-empty provenance"):
            normalize_stream(
                native_stream,
                workflow="research",
                run_id="bad-provenance",
                langgraph_version=PINNED_LANGGRAPH_VERSION,
            )


if __name__ == "__main__":
    unittest.main()
