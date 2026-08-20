"""Systematic, controlled mutations for checker conformance experiments.

Every case starts from a canonical accepted trace and carries the violation code
that the checker is expected to report.  The module constructs cases in memory;
it deliberately does not write experimental results.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


Trace = list[dict[str, Any]]
Rules = dict[str, Any]
Checker = Callable[[Trace, Rules], Mapping[str, Any]]
Mutation = Callable[[Trace, Rules], tuple[Trace, int]]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_DIR = REPOSITORY_ROOT / "prototype" / "traces"
DEFAULT_RULES_PATH = REPOSITORY_ROOT / "prototype" / "rules.json"


@dataclass(frozen=True)
class MutationCase:
    """A mutated trace and the diagnostic it is intended to trigger."""

    name: str
    expected_code: str
    description: str
    canonical_trace: str
    target_step: int
    trace: Trace

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "mutation": self.name,
            "expected_code": self.expected_code,
            "description": self.description,
            "canonical_trace": self.canonical_trace,
            "target_step": self.target_step,
        }

    def as_record(self) -> dict[str, Any]:
        """Return a JSON-serialisable experiment record."""

        return {"metadata": self.metadata, "trace": copy.deepcopy(self.trace)}


@dataclass(frozen=True)
class MutationSpec:
    name: str
    expected_code: str
    description: str
    canonical_trace: str
    mutate: Mutation


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _renumber(trace: Trace) -> Trace:
    for step, event in enumerate(trace, start=1):
        event["step"] = step
    return trace


def _event_index(
    trace: Trace,
    event_type: str,
    *,
    reverse: bool = False,
    predicate: Callable[[dict[str, Any]], bool] | None = None,
) -> int:
    indices: Iterable[int] = range(len(trace) - 1, -1, -1) if reverse else range(len(trace))
    for index in indices:
        event = trace[index]
        if event.get("event") == event_type and (predicate is None or predicate(event)):
            return index
    raise ValueError(f"canonical trace has no suitable '{event_type}' event")


def _fresh_trace_id(trace: Trace, stem: str) -> str:
    used = {event.get("trace") for event in trace}
    candidate = stem
    suffix = 1
    while candidate in used:
        suffix += 1
        candidate = f"{stem}-{suffix}"
    return candidate


def _first_shared_write(trace: Trace) -> dict[str, Any]:
    for event in trace:
        for write in event.get("writes", []):
            if write.get("scope") == "shared" and write.get("key"):
                return copy.deepcopy(write)
    raise ValueError("canonical trace has no shared-memory write")


def _unauthorised_tool(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "tool_call", reverse=True)
    event = trace[index]
    allowed = set(rules["tools"][event["tool"]].get("allowed_agents", []))
    event["agent"] = next(agent for agent in rules["agents"] if agent not in allowed)
    return trace, index + 1


def _overspend(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    index = _event_index(
        trace,
        "tool_call",
        predicate=lambda event: event.get("tool") == "BibliographicSearch",
    )
    template = copy.deepcopy(trace[index])
    template.pop("writes", None)
    template.pop("query", None)
    cost = int(rules["tools"][template["tool"]]["cost"])
    agent = template["agent"]
    spent = sum(
        int(rules["tools"][event["tool"]]["cost"])
        for event in trace
        if event.get("event") == "tool_call"
        and event.get("agent") == agent
        and event.get("tool") in rules["tools"]
    )
    remaining = int(rules["initial_budgets"][agent]) - spent
    successful_calls = max(0, remaining // cost)
    insert_at = len(trace)
    for offset in range(successful_calls + 1):
        event = copy.deepcopy(template)
        event["trace"] = _fresh_trace_id(trace, f"mut-overspend-{offset + 1}")
        trace.insert(insert_at + offset, event)
    _renumber(trace)
    return trace, insert_at + successful_calls + 1


def _illegal_handoff(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "handoff", reverse=True)
    event = trace[index]
    allowed = set(rules["interaction_graph"].get(event["from"], []))
    event["to"] = next(agent for agent in rules["agents"] if agent not in allowed and agent != event["from"])
    return trace, index + 1


def _illegal_message(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "message", reverse=True)
    event = trace[index]
    allowed = set(rules["interaction_graph"].get(event["from"], []))
    event["to"] = next(agent for agent in rules["agents"] if agent not in allowed and agent != event["from"])
    return trace, index + 1


def _payload_policy(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "handoff", reverse=True)
    trace[index]["payload"] = ""
    return trace, index + 1


def _missing_provenance(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    writer = next(iter(rules["agents"]))
    event = {
        "event": "shared_memory_update",
        "agent": writer,
        "trace": _fresh_trace_id(trace, "mut-missing-provenance"),
        "writes": [
            {
                "scope": "shared",
                "key": "mut_source_without_provenance",
                "value": "controlled mutation",
            }
        ],
    }
    trace.append(event)
    _renumber(trace)
    return trace, len(trace)


def _certificate_source(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    event = {
        "event": "certify",
        "agent": rules["certifiers"][0],
        "claim": "mut_orphan_claim",
        "source": "mut_missing_source",
        "trace": _fresh_trace_id(trace, "mut-certificate-source"),
    }
    trace.append(event)
    _renumber(trace)
    return trace, len(trace)


def _unauthorised_certifier(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    write = _first_shared_write(trace)
    certifiers = set(rules["certifiers"])
    event = {
        "event": "certify",
        "agent": next(agent for agent in rules["agents"] if agent not in certifiers),
        "claim": "mut_unauthorised_certification",
        "source": write["key"],
        "trace": _fresh_trace_id(trace, "mut-unauthorised-certifier"),
    }
    trace.append(event)
    _renumber(trace)
    return trace, len(trace)


def _duplicate_audit(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "answer", reverse=True)
    trace[index]["trace"] = trace[index - 1]["trace"]
    return trace, index + 1


def _missing_audit(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "answer", reverse=True)
    trace[index].pop("trace", None)
    return trace, index + 1


def _memory_overwrite(trace: Trace, rules: Rules) -> tuple[Trace, int]:
    write = _first_shared_write(trace)
    write["value"] = "controlled overwrite"
    event = {
        "event": "shared_memory_update",
        "agent": next(iter(rules["agents"])),
        "trace": _fresh_trace_id(trace, "mut-memory-overwrite"),
        "writes": [write],
    }
    provenance = write.get("provenance") or write.get("prov")
    if isinstance(provenance, dict):
        provenance["event"] = "shared_memory_update"
        provenance["agent"] = event["agent"]
        provenance["trace"] = event["trace"]
    trace.append(event)
    _renumber(trace)
    return trace, len(trace)


def _uncertified_claim(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "answer", reverse=True)
    trace[index]["claims"] = ["mut_uncertified_claim"]
    return trace, index + 1


def _unknown_tool(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "tool_call", reverse=True)
    trace[index]["tool"] = "MutUnknownTool"
    return trace, index + 1


def _unknown_agent(trace: Trace, _rules: Rules) -> tuple[Trace, int]:
    index = _event_index(trace, "answer", reverse=True)
    trace[index]["agent"] = "MutUnknownAgent"
    return trace, index + 1


MUTATION_SPECS: tuple[MutationSpec, ...] = (
    MutationSpec("unauthorised_tool", "tool_permission", "Use a known tool from an agent without permission.", "valid_research_swarm.json", _unauthorised_tool),
    MutationSpec("overspend", "insufficient_budget", "Insert one tool call beyond the actor's available budget.", "valid_research_swarm.json", _overspend),
    MutationSpec("illegal_handoff", "illegal_handoff", "Redirect a handoff to a known but disallowed endpoint.", "valid_research_swarm.json", _illegal_handoff),
    MutationSpec("invalid_message", "illegal_message", "Redirect a message to a known but disallowed endpoint.", "valid_research_swarm.json", _illegal_message),
    MutationSpec("payload_policy", "payload_policy", "Replace a required non-empty payload with an empty string.", "valid_research_swarm.json", _payload_policy),
    MutationSpec("missing_provenance", "missing_provenance", "Append a shared write without provenance metadata.", "valid_research_swarm.json", _missing_provenance),
    MutationSpec("missing_certificate_source", "certificate_source", "Append a certificate referencing an absent source key.", "valid_research_swarm.json", _certificate_source),
    MutationSpec("unauthorised_certifier", "unauthorized_certifier", "Append a certificate emitted by a known but unauthorised agent.", "valid_research_swarm.json", _unauthorised_certifier),
    MutationSpec("duplicate_audit", "duplicate_audit", "Reuse the preceding event's audit identifier.", "valid_research_swarm.json", _duplicate_audit),
    MutationSpec("missing_audit", "missing_audit", "Remove the audit identifier from an auditable event.", "valid_research_swarm.json", _missing_audit),
    MutationSpec("memory_overwrite", "memory_overwrite", "Append a write to an already allocated shared key.", "valid_research_swarm.json", _memory_overwrite),
    MutationSpec("uncertified_answer", "uncertified_claim", "Make the final answer cite a claim that was never certified.", "valid_research_swarm.json", _uncertified_claim),
    MutationSpec("unknown_tool", "unknown_tool", "Replace a terminal tool call with an unknown tool identifier.", "valid_research_swarm.json", _unknown_tool),
    MutationSpec("unknown_agent", "unknown_agent", "Replace the final answering agent with an unknown identifier.", "valid_research_swarm.json", _unknown_agent),
)


def generate_mutation_cases(
    *,
    trace_dir: Path = DEFAULT_TRACE_DIR,
    rules: Rules | None = None,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> list[MutationCase]:
    """Build the complete E3 mutation suite without modifying source traces."""

    active_rules = copy.deepcopy(rules) if rules is not None else load_json(rules_path)
    canonical_cache: dict[str, Trace] = {}
    cases: list[MutationCase] = []
    for spec in MUTATION_SPECS:
        if spec.canonical_trace not in canonical_cache:
            canonical_cache[spec.canonical_trace] = load_json(trace_dir / spec.canonical_trace)
        cases.extend(
            _generate_cases_from_specs(
                canonical_cache[spec.canonical_trace],
                canonical_name=spec.canonical_trace,
                rules=active_rules,
                specs=(spec,),
            )
        )
    return cases


def _generate_cases_from_specs(
    canonical_trace: Trace,
    *,
    canonical_name: str,
    rules: Rules,
    specs: Iterable[MutationSpec],
) -> list[MutationCase]:
    cases: list[MutationCase] = []
    for spec in specs:
        trace = copy.deepcopy(canonical_trace)
        mutated, target_step = spec.mutate(trace, copy.deepcopy(rules))
        cases.append(
            MutationCase(
                name=spec.name,
                expected_code=spec.expected_code,
                description=spec.description,
                canonical_trace=canonical_name,
                target_step=target_step,
                trace=_renumber(mutated),
            )
        )
    return cases


def generate_mutation_cases_from_trace(
    canonical_trace: Trace,
    *,
    canonical_name: str,
    rules: Rules,
) -> list[MutationCase]:
    """Derive all controlled mutations from one framework-generated trace.

    The input remains untouched.  A ``ValueError`` is raised if a canonical
    trace does not exercise the event shape required by one of the declared
    mutation categories; callers should treat that as an experimental coverage
    failure rather than silently substituting an unrelated handcrafted trace.
    """

    if not canonical_name.strip():
        raise ValueError("canonical_name must be a non-empty string")
    return _generate_cases_from_specs(
        canonical_trace,
        canonical_name=canonical_name,
        rules=rules,
        specs=MUTATION_SPECS,
    )


def violation_codes(result: Mapping[str, Any]) -> set[str]:
    """Extract stable diagnostic codes from a checker result."""

    codes: set[str] = set()
    for violation in result.get("violations", []):
        if isinstance(violation, str):
            codes.add(violation)
        elif isinstance(violation, Mapping) and violation.get("code"):
            codes.add(str(violation["code"]))
    return codes


def evaluate_mutation(case: MutationCase, rules: Rules, checker: Checker) -> dict[str, Any]:
    """Execute one case and report whether its expected code was observed."""

    result = dict(checker(copy.deepcopy(case.trace), copy.deepcopy(rules)))
    observed = sorted(violation_codes(result))
    violations = [
        dict(violation)
        for violation in result.get("violations", [])
        if isinstance(violation, Mapping)
    ]
    expected_at_target = any(
        violation.get("code") == case.expected_code
        and violation.get("step") == case.target_step
        for violation in violations
    )
    return {
        **case.metadata,
        "accepted": bool(result.get("accepted", False)),
        "observed_codes": observed,
        "detected": case.expected_code in observed,
        "expected_at_target_step": expected_at_target,
        "diagnostic_exact": observed == [case.expected_code],
        "diagnostic_count": len(violations),
        "violations": violations,
    }


def evaluate_mutation_suite(cases: Iterable[MutationCase], rules: Rules, checker: Checker) -> list[dict[str, Any]]:
    """Evaluate cases in deterministic input order."""

    return [evaluate_mutation(case, rules, checker) for case in cases]
