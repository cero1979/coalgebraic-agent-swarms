#!/usr/bin/env python3
"""Trace checker for resource-aware tool-augmented agent swarms.

The checker is intentionally small: it is not a full SELL prover.  It is an
executable abstraction of the paper's resource discipline.  It validates that
multi-agent traces respect graph constraints, tool permissions, linear budgets,
shared-memory provenance, certification, and audit-trace obligations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TraceState:
    budgets: dict[str, int]
    shared_memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    certified_claims: set[tuple[str, str]] = field(default_factory=set)
    certified_claim_order: list[tuple[str, str]] = field(default_factory=list)
    certified_claim_names: set[str] = field(default_factory=set)
    traces: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=lambda: {
        "events": 0,
        "tool_calls": 0,
        "handoffs": 0,
        "messages": 0,
        "memory_writes": 0,
        "certificates": 0,
        "answers": 0,
        "trace_items": 0,
        "budget_consumed": 0,
    })


@dataclass(frozen=True)
class Violation:
    code: str
    step: Any
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "step": self.step, "message": self.message}


@dataclass(frozen=True)
class ToolRule:
    allowed_agents: frozenset[str]
    cost: int


@dataclass(frozen=True)
class RuleIndex:
    agents: frozenset[str]
    edges: frozenset[tuple[str, str]]
    initial_budgets: dict[str, int]
    tools: dict[str, ToolRule]
    certifiers: frozenset[str]
    payload_policies: dict[str, str]
    required_events: frozenset[str]


@dataclass
class EventPlan:
    violations: list[Violation] = field(default_factory=list)
    trace_id: str | None = None
    event_counter: str | None = None
    budget_debit: tuple[str, int] | None = None
    shared_writes: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    local_write_count: int = 0
    certified_claim: tuple[str, str] | None = None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def index_rules(rules: dict[str, Any]) -> RuleIndex:
    edges = frozenset(
        (source, target)
        for source, targets in rules.get("interaction_graph", {}).items()
        for target in targets
    )
    tools = {
        name: ToolRule(
            allowed_agents=frozenset(spec.get("allowed_agents", [])),
            cost=int(spec.get("cost", 0)),
        )
        for name, spec in rules.get("tools", {}).items()
    }
    return RuleIndex(
        agents=frozenset(rules.get("agents", [])),
        edges=edges,
        initial_budgets=dict(rules.get("initial_budgets", {})),
        tools=tools,
        certifiers=frozenset(rules.get("certifiers", [])),
        payload_policies=dict(rules.get("payload_policies", {})),
        required_events=frozenset(rules.get("trace_required_for", [])),
    )


def add_violation(plan: EventPlan, code: str, step: Any, message: str) -> None:
    plan.violations.append(Violation(code=code, step=step, message=message))


def record_violations(state: TraceState, violations: list[Violation]) -> None:
    state.violations.extend(violations)
    state.errors.extend(f"step {item.step}: {item.message}" for item in violations)


def require_known_agent(
    plan: EventPlan,
    step: Any,
    agent: Any,
    agents: frozenset[str],
    role: str,
) -> bool:
    if not isinstance(agent, str):
        add_violation(
            plan,
            "unknown_agent",
            step,
            f"invalid {role} agent identifier {agent!r}",
        )
        return False
    if not agent.strip():
        add_violation(plan, "unknown_agent", step, f"missing {role} agent")
        return False
    if agent not in agents:
        add_violation(plan, "unknown_agent", step, f"unknown {role} agent '{agent}'")
        return False
    return True


def validate_trace(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    required_events: frozenset[str],
) -> None:
    event_type = event.get("event")
    trace_id = event.get("trace")
    valid_trace_id = isinstance(trace_id, str) and bool(trace_id.strip())
    if event_type in required_events and not valid_trace_id:
        add_violation(
            plan,
            "missing_audit",
            step,
            f"event '{event_type}' lacks required audit trace",
        )
        return
    if trace_id is not None and not valid_trace_id:
        add_violation(
            plan,
            "missing_audit",
            step,
            f"event '{event_type}' has an invalid audit trace identifier",
        )
        return
    if valid_trace_id:
        if trace_id in state.traces:
            add_violation(
                plan,
                "duplicate_audit",
                step,
                f"duplicate trace id '{trace_id}'",
            )
        else:
            plan.trace_id = trace_id


def allowed_edge(index: RuleIndex, source: str, target: str) -> bool:
    return (source, target) in index.edges


def payload_allowed(index: RuleIndex, event_type: str, event: dict[str, Any]) -> bool:
    mode = index.payload_policies.get(event_type, "allow_all")
    if mode == "allow_all":
        return True
    if mode == "nonempty_string":
        payload = event.get("payload")
        return isinstance(payload, str) and bool(payload.strip())
    raise ValueError(f"unsupported payload policy '{mode}' for '{event_type}'")


def has_explicit_provenance(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and any(has_explicit_provenance(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and any(has_explicit_provenance(item) for item in value)
    return bool(value)


def validate_writes(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
) -> None:
    trace_id = event.get("trace")
    writes = event.get("writes", [])
    if not isinstance(writes, list):
        add_violation(plan, "invalid_writes", step, "event writes must be a list")
        return

    pending_shared_keys: set[str] = set()
    for write in writes:
        if not isinstance(write, dict):
            add_violation(plan, "invalid_write", step, "memory write must be an object")
            continue
        scope = write.get("scope")
        key = write.get("key")
        if not isinstance(key, str) or not key.strip():
            add_violation(plan, "missing_memory_key", step, "memory write without key")
            continue
        if scope == "shared":
            provenance = write.get("provenance")
            if not has_explicit_provenance(provenance):
                add_violation(
                    plan,
                    "missing_provenance",
                    step,
                    f"shared memory write '{key}' lacks explicit provenance",
                )
            if key in state.shared_memory or key in pending_shared_keys:
                add_violation(
                    plan,
                    "memory_overwrite",
                    step,
                    f"shared memory key '{key}' already exists",
                )
                continue
            pending_shared_keys.add(key)
            plan.shared_writes.append((key, {
                "event": event.get("event"),
                "agent": event.get("agent"),
                "tool": event.get("tool"),
                "step": step,
                "trace": trace_id,
                "value": write.get("value"),
                "provenance": provenance,
            }))
        elif scope == "local":
            plan.local_write_count += 1
        else:
            add_violation(
                plan,
                "memory_scope",
                step,
                f"unsupported memory scope '{scope}'",
            )


def validate_tool_call(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    plan.event_counter = "tool_calls"
    agent = event.get("agent")
    tool = event.get("tool")
    known_agent = require_known_agent(plan, step, agent, index.agents, "tool-calling")
    spec = index.tools.get(tool) if isinstance(tool, str) else None
    if spec is None:
        add_violation(plan, "unknown_tool", step, f"unknown tool '{tool}'")
    elif known_agent:
        if agent not in spec.allowed_agents:
            add_violation(
                plan,
                "tool_permission",
                step,
                f"agent '{agent}' lacks permission for tool '{tool}'",
            )
        remaining = state.budgets.get(agent, 0)
        if remaining < spec.cost:
            add_violation(
                plan,
                "insufficient_budget",
                step,
                f"insufficient budget for '{agent}': required {spec.cost}, available {remaining}",
            )
        else:
            plan.budget_debit = (agent, spec.cost)
    validate_writes(state, plan, step, event)


def validate_handoff(
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    plan.event_counter = "handoffs"
    source = event.get("from")
    target = event.get("to")
    ok_source = require_known_agent(plan, step, source, index.agents, "source")
    ok_target = require_known_agent(plan, step, target, index.agents, "target")
    if ok_source and ok_target and not allowed_edge(index, source, target):
        add_violation(
            plan,
            "illegal_handoff",
            step,
            f"handoff edge '{source} -> {target}' is not allowed",
        )
    if not payload_allowed(index, "handoff", event):
        add_violation(
            plan,
            "payload_policy",
            step,
            "handoff payload violates configured policy",
        )


def validate_message(
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    plan.event_counter = "messages"
    source = event.get("from")
    target = event.get("to")
    ok_source = require_known_agent(plan, step, source, index.agents, "source")
    ok_target = require_known_agent(plan, step, target, index.agents, "target")
    if ok_source and ok_target and not allowed_edge(index, source, target):
        add_violation(
            plan,
            "illegal_message",
            step,
            f"message edge '{source} -> {target}' is not allowed",
        )
    if not payload_allowed(index, "message", event):
        add_violation(
            plan,
            "payload_policy",
            step,
            "message payload violates configured policy",
        )


def validate_certify(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    plan.event_counter = "certificates"
    agent = event.get("agent")
    known_agent = require_known_agent(plan, step, agent, index.agents, "certifying")
    if known_agent and agent not in index.certifiers:
        add_violation(
            plan,
            "unauthorized_certifier",
            step,
            f"agent '{agent}' is not authorised to certify claims",
        )
    claim = event.get("claim")
    source = event.get("source")
    valid_claim = isinstance(claim, str) and bool(claim.strip())
    valid_source = isinstance(source, str) and bool(source.strip())
    if not valid_claim:
        add_violation(
            plan,
            "missing_claim",
            step,
            "certificate claim must be a non-empty string",
        )
    if not valid_source:
        add_violation(
            plan,
            "certificate_source",
            step,
            "certificate source must be a non-empty string",
        )
    elif source not in state.shared_memory:
        add_violation(
            plan,
            "certificate_source",
            step,
            f"certificate source '{source}' not found in shared memory",
        )
    if valid_claim and valid_source and source in state.shared_memory:
        plan.certified_claim = (claim, source)


def validate_answer(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    plan.event_counter = "answers"
    agent = event.get("agent")
    require_known_agent(plan, step, agent, index.agents, "answering")
    claims = event.get("claims", [])
    if not isinstance(claims, list):
        add_violation(plan, "invalid_claims", step, "answer claims must be a list")
        return
    for claim in claims:
        if not isinstance(claim, str) or claim not in state.certified_claim_names:
            add_violation(
                plan,
                "uncertified_claim",
                step,
                f"answer uses uncertified claim '{claim}'",
            )


def validate_memory_update(
    state: TraceState,
    plan: EventPlan,
    step: Any,
    event: dict[str, Any],
    index: RuleIndex,
) -> None:
    agent = event.get("agent")
    require_known_agent(plan, step, agent, index.agents, "memory-writing")
    writes = event.get("writes", [])
    if isinstance(writes, list) and not writes:
        add_violation(
            plan,
            "invalid_writes",
            step,
            "shared-memory update requires at least one write",
        )
    validate_writes(state, plan, step, event)


def commit_plan(state: TraceState, plan: EventPlan) -> None:
    if plan.trace_id is not None:
        state.traces.add(plan.trace_id)
        state.counters["trace_items"] += 1
    if plan.budget_debit is not None:
        agent, cost = plan.budget_debit
        state.budgets[agent] -= cost
        state.counters["budget_consumed"] += cost
    for key, record in plan.shared_writes:
        state.shared_memory[key] = record
    state.counters["memory_writes"] += len(plan.shared_writes) + plan.local_write_count
    if plan.certified_claim is not None:
        if plan.certified_claim not in state.certified_claims:
            state.certified_claim_order.append(plan.certified_claim)
        state.certified_claims.add(plan.certified_claim)
        state.certified_claim_names.add(plan.certified_claim[0])
    if plan.event_counter is not None:
        state.counters[plan.event_counter] += 1


def build_trace_result(state: TraceState) -> dict[str, Any]:
    return {
        "accepted": not state.errors,
        "errors": state.errors,
        "violations": [item.as_dict() for item in state.violations],
        "final_budgets": state.budgets,
        "shared_memory": list(state.shared_memory),
        "shared_provenance": state.shared_memory,
        "certified_claims": list(dict.fromkeys(
            claim for claim, _source in state.certified_claim_order
        )),
        "certified_claim_sources": [
            {"claim": claim, "source": source}
            for claim, source in state.certified_claim_order
        ],
        "counters": state.counters,
    }


def check_trace(trace: list[dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    rule_index = index_rules(rules)
    state = TraceState(budgets=dict(rule_index.initial_budgets))
    if not isinstance(trace, list):
        invalid_plan = EventPlan()
        add_violation(
            invalid_plan,
            "unknown_event",
            0,
            "trace must be a JSON array of event objects",
        )
        record_violations(state, invalid_plan.violations)
        return build_trace_result(state)

    for position, event in enumerate(trace, start=1):
        if not isinstance(event, dict):
            step = position
            state.counters["events"] += 1
            invalid_plan = EventPlan()
            add_violation(
                invalid_plan,
                "unknown_event",
                step,
                "trace event must be an object",
            )
            record_violations(state, invalid_plan.violations)
            continue

        step = event.get("step", position)
        state.counters["events"] += 1
        plan = EventPlan()
        if type(step) is not int or step != position:
            add_violation(
                plan,
                "nonsequential_step",
                step,
                f"invalid or non-sequential step number, expected integer {position}",
            )
        event_type = event.get("event")
        if not isinstance(event_type, str) or not event_type:
            add_violation(
                plan,
                "unknown_event",
                step,
                f"unknown event type '{event_type}'",
            )
            record_violations(state, plan.violations)
            continue
        validate_trace(state, plan, step, event, rule_index.required_events)

        if event_type == "tool_call":
            validate_tool_call(state, plan, step, event, rule_index)
        elif event_type == "handoff":
            validate_handoff(plan, step, event, rule_index)
        elif event_type == "message":
            validate_message(plan, step, event, rule_index)
        elif event_type == "certify":
            validate_certify(state, plan, step, event, rule_index)
        elif event_type == "answer":
            validate_answer(state, plan, step, event, rule_index)
        elif event_type == "shared_memory_update":
            validate_memory_update(state, plan, step, event, rule_index)
        else:
            add_violation(
                plan,
                "unknown_event",
                step,
                f"unknown event type '{event_type}'",
            )

        if plan.violations:
            record_violations(state, plan.violations)
        else:
            commit_plan(state, plan)

    return build_trace_result(state)


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_\allowbreak{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sum_counters(results: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "events": 0,
        "tool_calls": 0,
        "handoffs": 0,
        "messages": 0,
        "memory_writes": 0,
        "certificates": 0,
        "answers": 0,
        "trace_items": 0,
        "budget_consumed": 0,
    }
    for result in results:
        for key in totals:
            totals[key] += int(result["counters"].get(key, 0))
    return totals


def build_coverage_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [result for result in results if result["accepted"]]
    rejected = [result for result in results if not result["accepted"]]
    accepted_event_types = sorted({
        event_type
        for result in accepted
        for event_type in result.get("event_types", [])
    })
    rejected_codes = {
        violation["code"]
        for result in rejected
        for violation in result.get("violations", [])
    }
    accepted_framework_styles = sorted({
        style
        for result in accepted
        for style in result.get("framework_styles", [])
    })

    obligations = {
        "known_participating_agents": {
            "positive": bool(accepted),
            "negative": "unknown_agent" in rejected_codes,
        },
        "graph_edges_for_handoffs_messages": {
            "positive": any({"handoff", "message"} & set(result.get("event_types", [])) for result in accepted),
            "negative": bool({"illegal_handoff", "illegal_message"} & rejected_codes),
        },
        "handoff_message_payload_policy": {
            "positive": any({"handoff", "message"} & set(result.get("event_types", [])) for result in accepted),
            "negative": "payload_policy" in rejected_codes,
        },
        "tool_permission_and_known_tools": {
            "positive": "tool_call" in accepted_event_types,
            "negative": bool({"tool_permission", "unknown_tool"} & rejected_codes),
        },
        "linear_budget_consumption": {
            "positive": any(result["counters"].get("budget_consumed", 0) > 0 for result in accepted),
            "negative": "insufficient_budget" in rejected_codes,
        },
        "append_only_shared_memory": {
            "positive": any(result["counters"].get("memory_writes", 0) > 0 for result in accepted),
            "negative": bool({"memory_overwrite", "memory_scope"} & rejected_codes),
        },
        "fresh_audit_evidence": {
            "positive": all(result["counters"].get("trace_items", 0) > 0 for result in accepted),
            "negative": bool({"missing_audit", "duplicate_audit"} & rejected_codes),
        },
        "claim_source_certification": {
            "positive": any(result["counters"].get("certificates", 0) > 0 for result in accepted),
            "negative": bool({"certificate_source", "unauthorized_certifier"} & rejected_codes),
        },
        "answer_cites_certified_claims": {
            "positive": any(result["counters"].get("answers", 0) > 0 for result in accepted),
            "negative": "uncertified_claim" in rejected_codes,
        },
        "framework_style_normalisation": {
            "positive": bool(accepted_framework_styles),
            "negative": False,
        },
    }

    return {
        "trace_count": len(results),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_traces": [result["trace"] for result in accepted],
        "rejected_traces": [result["trace"] for result in rejected],
        "accepted_event_types": accepted_event_types,
        "accepted_framework_styles": accepted_framework_styles,
        "aggregate_counters_all": sum_counters(results),
        "aggregate_counters_accepted": sum_counters(accepted),
        "obligation_coverage": obligations,
    }


def write_coverage_table(path: Path, summary: dict[str, Any]) -> None:
    rows = [
        ("Total traces", str(summary["trace_count"])),
        ("Accepted traces", str(summary["accepted_count"])),
        ("Rejected controls", str(summary["rejected_count"])),
        ("Accepted event types", ", ".join(summary["accepted_event_types"])),
        ("Accepted framework styles", ", ".join(summary["accepted_framework_styles"]) or "none"),
        ("Accepted events", str(summary["aggregate_counters_accepted"]["events"])),
        ("Accepted budget consumed", str(summary["aggregate_counters_accepted"]["budget_consumed"])),
    ]
    with path.open("w", encoding="utf-8") as handle:
        handle.write("% Generated by prototype/checker.py. Do not edit manually.\n")
        handle.write("\\begin{table}[htbp]\n")
        handle.write("\\centering\n")
        handle.write("\\small\n")
        handle.write("\\begin{tabular}{>{\\raggedright\\arraybackslash}p{0.38\\linewidth}>{\\raggedright\\arraybackslash}p{0.50\\linewidth}}\n")
        handle.write("\\toprule\n")
        handle.write("Metric & Value \\\\\n")
        handle.write("\\midrule\n")
        for metric, value in rows:
            handle.write(f"{latex_escape(metric)} & {latex_escape(value)} \\\\\n")
        handle.write("\\bottomrule\n")
        handle.write("\\end{tabular}\n")
        handle.write("\\caption{Coverage summary for the finite conformance suite. The table reports suite size, accepted behaviours, exercised event kinds, and aggregate accepted-resource usage.}\n")
        handle.write("\\label{tab:prototype-coverage}\n")
        handle.write("\\end{table}\n")


def write_manifest(path: Path, files: list[Path]) -> None:
    manifest = {
        "sha256": {str(file): sha256_file(file) for file in sorted(files, key=lambda item: str(item)) if file.exists()},
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def trace_metadata(trace: Any) -> tuple[list[str], list[str]]:
    event_types: set[str] = set()
    framework_styles: set[str] = set()
    if not isinstance(trace, list):
        return [], []
    for event in trace:
        if not isinstance(event, dict):
            continue
        event_type = event.get("event")
        if isinstance(event_type, str):
            event_types.add(event_type)
        framework = event.get("framework")
        if isinstance(framework, dict):
            style = framework.get("style")
            if isinstance(style, str) and style:
                framework_styles.add(style)
    return sorted(event_types), sorted(framework_styles)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate resource-aware multi-agent traces.")
    parser.add_argument("--rules", type=Path, required=True, help="Path to rules.json")
    parser.add_argument("--traces", type=Path, nargs="+", required=True, help="Trace JSON files")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for generated results")
    args = parser.parse_args()

    rules = load_json(args.rules)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for trace_path in sorted(args.traces):
        trace = load_json(trace_path)
        result = check_trace(trace, rules)
        event_types, framework_styles = trace_metadata(trace)
        result["trace"] = trace_path.name
        result["event_types"] = event_types
        result["framework_styles"] = framework_styles
        results.append(result)

    json_path = args.out_dir / "results.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    csv_path = args.out_dir / "results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["trace", "status", "events", "budget_consumed", "trace_items", "diagnostic"])
        for result in results:
            diagnostic = "OK" if result["accepted"] else result["errors"][0]
            counters = result["counters"]
            writer.writerow([
                result["trace"],
                "accepted" if result["accepted"] else "rejected",
                counters["events"],
                counters["budget_consumed"],
                counters["trace_items"],
                diagnostic,
            ])

    tex_path = args.out_dir / "results_table.tex"
    with tex_path.open("w", encoding="utf-8") as handle:
        handle.write("% Generated by prototype/checker.py. Do not edit manually.\n")
        handle.write("\\begin{table}[htbp]\n")
        handle.write("\\centering\n")
        handle.write("\\scriptsize\n")
        handle.write("\\setlength{\\tabcolsep}{3pt}\n")
        handle.write("\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.24\\linewidth}>{\\raggedright\\arraybackslash}p{0.10\\linewidth}rr>{\\raggedright\\arraybackslash}p{0.48\\linewidth}@{}}\n")
        handle.write("\\toprule\n")
        handle.write("Trace & Status & Events & Cost & Diagnostic \\\\\n")
        handle.write("\\midrule\n")
        for result in results:
            counters = result["counters"]
            status = "accepted" if result["accepted"] else "rejected"
            diagnostic = "OK" if result["accepted"] else result["errors"][0]
            row = [
                latex_escape(result["trace"].replace(".json", "")),
                latex_escape(status),
                str(counters["events"]),
                str(counters["budget_consumed"]),
                latex_escape(diagnostic),
            ]
            handle.write("{} & {} & {} & {} & {} \\\\\n".format(*row))
        handle.write("\\bottomrule\n")
        handle.write("\\end{tabular}\n")
        handle.write("\\caption{Results produced by the prototype trace checker. Accepted traces satisfy the graph, permission, budget, provenance, certification, and audit-trace constraints. Rejected traces illustrate violations of linear budget, certificate support, trace freshness, handoff topology, audit obligations, shared-memory append-only discipline, tool permission, and answer certification.}\n")
        handle.write("\\label{tab:prototype-results}\n")
        handle.write("\\end{table}\n")

    coverage_summary = build_coverage_summary(results)
    coverage_path = args.out_dir / "coverage_summary.json"
    with coverage_path.open("w", encoding="utf-8") as handle:
        json.dump(coverage_summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    coverage_table_path = args.out_dir / "coverage_table.tex"
    write_coverage_table(coverage_table_path, coverage_summary)

    manifest_path = args.out_dir / "MANIFEST.json"
    manifest_files = [
        Path("HIGHLIGHTS.md"),
        Path("cas-common.sty"),
        Path("cas-sc.cls"),
        Path("main.tex"),
        Path("prototype/checker.py"),
        Path("prototype/test_checker.py"),
        Path("prototype/verify_manifest.py"),
        args.rules,
        *sorted(args.traces),
        json_path,
        csv_path,
        tex_path,
        coverage_path,
        coverage_table_path,
    ]
    write_manifest(manifest_path, manifest_files)

    for result in results:
        status = "ACCEPT" if result["accepted"] else "REJECT"
        diagnostic = "OK" if result["accepted"] else result["errors"][0]
        print(f"{status:6} {result['trace']}: {diagnostic}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {tex_path}")
    print(f"Wrote {coverage_path}")
    print(f"Wrote {coverage_table_path}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
