from __future__ import annotations

import json
import unittest
from pathlib import Path

from checker import (
    check_trace,
    has_explicit_provenance,
    index_rules,
    trace_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "prototype/traces"
RULES = json.loads((ROOT / "prototype/rules.json").read_text(encoding="utf-8"))

EXPECTED_REJECTION_CODES = {
    "invalid_bad_memory_scope.json": {"memory_scope"},
    "invalid_budget_violation.json": {"insufficient_budget"},
    "invalid_certificate_source.json": {"certificate_source"},
    "invalid_duplicate_trace.json": {"duplicate_audit"},
    "invalid_handoff_violation.json": {"illegal_handoff"},
    "invalid_message_violation.json": {"illegal_message"},
    "invalid_missing_trace.json": {"missing_audit"},
    "invalid_payload_policy.json": {"payload_policy"},
    "invalid_shared_memory_overwrite.json": {"memory_overwrite"},
    "invalid_tool_permission.json": {"tool_permission"},
    "invalid_unauthorized_certifier.json": {"unauthorized_certifier"},
    "invalid_uncertified_answer.json": {"uncertified_claim"},
    "invalid_unknown_agent.json": {"unknown_agent"},
    "invalid_unknown_tool.json": {"unknown_tool"},
}

RESULT_KEYS = {
    "accepted",
    "errors",
    "violations",
    "final_budgets",
    "shared_memory",
    "shared_provenance",
    "certified_claims",
    "certified_claim_sources",
    "counters",
}


def load_trace(name: str) -> list[dict]:
    return json.loads((TRACE_DIR / name).read_text(encoding="utf-8"))


def violation_codes(result: dict) -> set[str]:
    return {item["code"] for item in result["violations"]}


class CheckerConformanceTests(unittest.TestCase):
    def test_suite_has_five_accepted_and_fourteen_rejected_traces(self) -> None:
        paths = sorted(TRACE_DIR.glob("*.json"))
        self.assertEqual(len(paths), 19)
        self.assertEqual(sum(path.name.startswith("valid_") for path in paths), 5)
        self.assertEqual(sum(path.name.startswith("invalid_") for path in paths), 14)

        for path in paths:
            with self.subTest(trace=path.name):
                result = check_trace(load_trace(path.name), RULES)
                self.assertEqual(result["accepted"], path.name.startswith("valid_"))

    def test_each_negative_control_has_its_stable_violation_code(self) -> None:
        self.assertEqual(
            set(EXPECTED_REJECTION_CODES),
            {path.name for path in TRACE_DIR.glob("invalid_*.json")},
        )
        for name, expected_codes in EXPECTED_REJECTION_CODES.items():
            with self.subTest(trace=name):
                result = check_trace(load_trace(name), RULES)
                self.assertFalse(result["accepted"])
                self.assertEqual(violation_codes(result), expected_codes)

    def test_result_preserves_old_keys_and_adds_structured_violations(self) -> None:
        result = check_trace(load_trace("invalid_unknown_tool.json"), RULES)
        self.assertTrue(RESULT_KEYS.issubset(result))
        self.assertEqual(
            result["violations"],
            [
                {
                    "code": "unknown_tool",
                    "step": 1,
                    "message": "unknown tool 'NonexistentTool'",
                }
            ],
        )
        self.assertEqual(
            result["errors"],
            [f"step {item['step']}: {item['message']}" for item in result["violations"]],
        )

    def test_all_valid_shared_writes_have_explicit_provenance(self) -> None:
        for path in sorted(TRACE_DIR.glob("valid_*.json")):
            with self.subTest(trace=path.name):
                trace = load_trace(path.name)
                shared_writes = [
                    write
                    for event in trace
                    for write in event.get("writes", [])
                    if write.get("scope") == "shared"
                ]
                self.assertTrue(shared_writes)
                self.assertTrue(
                    all(has_explicit_provenance(write.get("provenance")) for write in shared_writes)
                )

    def test_rule_index_precomputes_constant_time_membership_structures(self) -> None:
        index = index_rules(RULES)
        self.assertIsInstance(index.agents, frozenset)
        self.assertIsInstance(index.edges, frozenset)
        self.assertIsInstance(index.certifiers, frozenset)
        self.assertIsInstance(index.tools["BibliographicSearch"].allowed_agents, frozenset)
        self.assertIn(("Planner", "Retriever"), index.edges)


class CheckerTransactionTests(unittest.TestCase):
    def test_rejected_event_does_not_commit_any_ledger_effect(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "tool_call",
                "agent": "Planner",
                "tool": "BibliographicSearch",
                "trace": "tr-invalid-permission",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "should_not_exist",
                        "value": "x",
                        "provenance": "synthetic transaction fixture",
                    }
                ],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertFalse(result["accepted"])
        self.assertEqual(violation_codes(result), {"tool_permission"})
        self.assertEqual(result["final_budgets"], RULES["initial_budgets"])
        self.assertEqual(result["shared_memory"], [])
        self.assertEqual(result["counters"]["events"], 1)
        self.assertEqual(result["counters"]["tool_calls"], 0)
        self.assertEqual(result["counters"]["budget_consumed"], 0)
        self.assertEqual(result["counters"]["memory_writes"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_one_invalid_write_rolls_back_the_whole_event(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "tool_call",
                "agent": "Retriever",
                "tool": "BibliographicSearch",
                "trace": "tr-atomic",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "would_be_valid",
                        "value": "x",
                        "provenance": "synthetic valid provenance",
                    },
                    {
                        "scope": "shared",
                        "key": "missing_provenance",
                        "value": "y",
                    },
                ],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(violation_codes(result), {"missing_provenance"})
        self.assertEqual(result["final_budgets"], RULES["initial_budgets"])
        self.assertEqual(result["shared_memory"], [])
        self.assertEqual(result["counters"]["tool_calls"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_audit_id_from_rejected_event_can_be_used_by_later_valid_event(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "tool_call",
                "agent": "Retriever",
                "tool": "BibliographicSearch",
                "trace": "tr-reusable-after-reject",
                "writes": [
                    {"scope": "shared", "key": "bad", "value": "x"}
                ],
            },
            {
                "step": 2,
                "event": "tool_call",
                "agent": "Retriever",
                "tool": "BibliographicSearch",
                "trace": "tr-reusable-after-reject",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "good",
                        "value": "y",
                        "provenance": "synthetic valid provenance",
                    }
                ],
            },
        ]
        result = check_trace(trace, RULES)
        self.assertFalse(result["accepted"])
        self.assertEqual(violation_codes(result), {"missing_provenance"})
        self.assertEqual(result["shared_memory"], ["good"])
        self.assertEqual(result["final_budgets"]["Retriever"], 3)
        self.assertEqual(result["counters"]["events"], 2)
        self.assertEqual(result["counters"]["tool_calls"], 1)
        self.assertEqual(result["counters"]["trace_items"], 1)

    def test_duplicate_keys_inside_one_event_commit_nothing(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-intra-event-duplicate",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "same",
                        "value": "first",
                        "provenance": "synthetic first provenance",
                    },
                    {
                        "scope": "shared",
                        "key": "same",
                        "value": "second",
                        "provenance": "synthetic second provenance",
                    },
                ],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(violation_codes(result), {"memory_overwrite"})
        self.assertEqual(result["shared_memory"], [])
        self.assertEqual(result["counters"]["memory_writes"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_rejected_certification_does_not_support_a_later_answer(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-source",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "source",
                        "value": "source value",
                        "provenance": "synthetic source provenance",
                    }
                ],
            },
            {
                "step": 2,
                "event": "certify",
                "agent": "Planner",
                "claim": "claim",
                "source": "source",
                "trace": "tr-bad-certifier",
            },
            {
                "step": 3,
                "event": "answer",
                "agent": "Planner",
                "claims": ["claim"],
                "trace": "tr-answer",
            },
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(
            violation_codes(result),
            {"unauthorized_certifier", "uncertified_claim"},
        )
        self.assertEqual(result["certified_claims"], [])
        self.assertEqual(result["counters"]["certificates"], 0)
        self.assertEqual(result["counters"]["answers"], 0)
        self.assertEqual(result["counters"]["trace_items"], 1)


class CheckerViolationCodeTests(unittest.TestCase):
    def test_missing_provenance_has_stable_code(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-no-provenance",
                "writes": [{"scope": "shared", "key": "source", "value": "x"}],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(violation_codes(result), {"missing_provenance"})

    def test_unknown_event_has_stable_code(self) -> None:
        result = check_trace([{"step": 1, "event": "teleport"}], RULES)
        self.assertEqual(violation_codes(result), {"unknown_event"})

    def test_nonsequential_step_has_stable_code_and_no_effects(self) -> None:
        trace = [
            {
                "step": 2,
                "event": "handoff",
                "from": "Planner",
                "to": "Retriever",
                "payload": "valid except for its step",
                "trace": "tr-wrong-step",
            }
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(violation_codes(result), {"nonsequential_step"})
        self.assertEqual(result["counters"]["handoffs"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_boolean_and_float_steps_are_not_json_integers(self) -> None:
        for step in (True, 1.0):
            with self.subTest(step=step):
                result = check_trace(
                    [
                        {
                            "step": step,
                            "event": "handoff",
                            "from": "Planner",
                            "to": "Retriever",
                            "payload": "otherwise valid",
                            "trace": f"tr-invalid-step-{step!r}",
                        }
                    ],
                    RULES,
                )
                self.assertEqual(violation_codes(result), {"nonsequential_step"})
                self.assertEqual(result["counters"]["handoffs"], 0)
                self.assertEqual(result["counters"]["trace_items"], 0)

    def test_non_object_event_and_non_array_trace_are_structured_rejections(self) -> None:
        event_result = check_trace([42], RULES)
        self.assertEqual(violation_codes(event_result), {"unknown_event"})
        self.assertEqual(event_result["counters"]["events"], 1)

        trace_result = check_trace({"event": "handoff"}, RULES)  # type: ignore[arg-type]
        self.assertEqual(violation_codes(trace_result), {"unknown_event"})
        self.assertEqual(trace_result["violations"][0]["step"], 0)

    def test_non_string_event_type_is_a_structured_rejection(self) -> None:
        result = check_trace([{"step": 1, "event": ["tool_call"]}], RULES)
        self.assertEqual(violation_codes(result), {"unknown_event"})

    def test_non_string_agent_and_tool_are_structured_rejections(self) -> None:
        result = check_trace(
            [
                {
                    "step": 1,
                    "event": "tool_call",
                    "agent": ["Retriever"],
                    "tool": ["BibliographicSearch"],
                    "trace": "tr-malformed-call",
                }
            ],
            RULES,
        )
        self.assertEqual(violation_codes(result), {"unknown_agent", "unknown_tool"})
        self.assertEqual(result["counters"]["tool_calls"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_malformed_certificate_fields_are_structured_rejections(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-cert-source",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "source",
                        "value": "x",
                        "provenance": "synthetic source provenance",
                    }
                ],
            },
            {
                "step": 2,
                "event": "certify",
                "agent": "Verifier",
                "claim": ["claim"],
                "source": ["source"],
                "trace": "tr-malformed-cert",
            },
        ]
        result = check_trace(trace, RULES)
        self.assertEqual(violation_codes(result), {"missing_claim", "certificate_source"})
        self.assertEqual(result["certified_claims"], [])
        self.assertEqual(result["counters"]["certificates"], 0)

    def test_non_string_answer_claim_is_an_uncertified_claim(self) -> None:
        result = check_trace(
            [
                {
                    "step": 1,
                    "event": "answer",
                    "agent": "Planner",
                    "claims": [{"claim": "not-a-string"}],
                    "trace": "tr-malformed-answer",
                }
            ],
            RULES,
        )
        self.assertEqual(violation_codes(result), {"uncertified_claim"})

    def test_invalid_claim_collection_has_stable_code(self) -> None:
        result = check_trace(
            [
                {
                    "step": 1,
                    "event": "answer",
                    "agent": "Planner",
                    "claims": {"claim": "not-a-list"},
                    "trace": "tr-invalid-claims",
                }
            ],
            RULES,
        )
        self.assertEqual(violation_codes(result), {"invalid_claims"})

    def test_invalid_writes_shapes_have_stable_codes(self) -> None:
        cases = (
            ("not-a-list", {"invalid_writes"}),
            ([42], {"invalid_write"}),
            ([{"scope": "shared", "value": "x", "provenance": "fixture"}], {"missing_memory_key"}),
        )
        for writes, expected_codes in cases:
            with self.subTest(writes=writes):
                result = check_trace(
                    [
                        {
                            "step": 1,
                            "event": "shared_memory_update",
                            "agent": "Retriever",
                            "writes": writes,
                            "trace": "tr-invalid-writes",
                        }
                    ],
                    RULES,
                )
                self.assertEqual(violation_codes(result), expected_codes)
                self.assertEqual(result["shared_memory"], [])
                self.assertEqual(result["counters"]["memory_writes"], 0)

    def test_empty_shared_memory_update_is_rejected(self) -> None:
        result = check_trace(
            [
                {
                    "step": 1,
                    "event": "shared_memory_update",
                    "agent": "Retriever",
                    "writes": [],
                    "trace": "tr-empty-update",
                }
            ],
            RULES,
        )
        self.assertEqual(violation_codes(result), {"invalid_writes"})
        self.assertEqual(result["counters"]["memory_writes"], 0)
        self.assertEqual(result["counters"]["trace_items"], 0)

    def test_non_string_audit_identifier_has_stable_code(self) -> None:
        result = check_trace(
            [
                {
                    "step": 1,
                    "event": "handoff",
                    "from": "Planner",
                    "to": "Retriever",
                    "payload": "valid payload",
                    "trace": ["not", "hashable"],
                }
            ],
            RULES,
        )
        self.assertEqual(violation_codes(result), {"missing_audit"})

    def test_trace_metadata_ignores_malformed_entries(self) -> None:
        event_types, frameworks = trace_metadata(
            [
                42,
                {"event": ["tool_call"]},
                {"event": "handoff", "framework": ["bad"]},
                {"event": "message", "framework": {"style": "langgraph-like"}},
            ]
        )
        self.assertEqual(event_types, ["handoff", "message"])
        self.assertEqual(frameworks, ["langgraph-like"])

    def test_local_write_does_not_require_shared_provenance(self) -> None:
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-local",
                "writes": [{"scope": "local", "key": "private", "value": "x"}],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["counters"]["memory_writes"], 1)

    def test_explicit_provenance_is_preserved_verbatim(self) -> None:
        provenance = {"kind": "fixture", "source": "deterministic-tool"}
        trace = [
            {
                "step": 1,
                "event": "shared_memory_update",
                "agent": "Retriever",
                "trace": "tr-provenance",
                "writes": [
                    {
                        "scope": "shared",
                        "key": "source",
                        "value": "x",
                        "provenance": provenance,
                    }
                ],
            }
        ]
        result = check_trace(trace, RULES)
        self.assertTrue(result["accepted"])
        self.assertEqual(
            result["shared_provenance"]["source"]["provenance"],
            provenance,
        )


if __name__ == "__main__":
    unittest.main()
