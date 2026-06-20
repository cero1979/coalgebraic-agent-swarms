#!/usr/bin/env python3
"""Trace checker for resource-aware tool-augmented agent swarms.

The checker is intentionally small: it is not a full SELL prover.  It is an
executable abstraction of the paper's resource discipline.  It validates that
multi-agent traces respect graph constraints, tool permissions, linear budgets,
shared-memory provenance, certification, and audit-trace obligations.
"""

from __future__ import annotations

import argparse
import copy
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
    traces: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
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


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def add_error(state: TraceState, step: Any, message: str) -> None:
    state.errors.append(f"step {step}: {message}")


def require_known_agent(state: TraceState, step: Any, agent: str | None, agents: set[str], role: str) -> bool:
    if not agent:
        add_error(state, step, f"missing {role} agent")
        return False
    if agent not in agents:
        add_error(state, step, f"unknown {role} agent '{agent}'")
        return False
    return True


def require_trace(state: TraceState, step: Any, event: dict[str, Any], required_events: set[str]) -> None:
    event_type = event.get("event")
    trace_id = event.get("trace")
    if event_type in required_events and not trace_id:
        add_error(state, step, f"event '{event_type}' lacks required audit trace")
        return
    if trace_id:
        if trace_id in state.traces:
            add_error(state, step, f"duplicate trace id '{trace_id}'")
        else:
            state.traces.add(trace_id)
            state.counters["trace_items"] += 1


def allowed_edge(rules: dict[str, Any], source: str, target: str) -> bool:
    return target in rules.get("interaction_graph", {}).get(source, [])


def payload_allowed(rules: dict[str, Any], event_type: str, event: dict[str, Any]) -> bool:
    mode = rules.get("payload_policies", {}).get(event_type, "allow_all")
    if mode == "allow_all":
        return True
    if mode == "nonempty_string":
        payload = event.get("payload")
        return isinstance(payload, str) and bool(payload.strip())
    raise ValueError(f"unsupported payload policy '{mode}' for '{event_type}'")


def record_writes(state: TraceState, step: Any, event: dict[str, Any]) -> None:
    trace_id = event.get("trace")
    for write in event.get("writes", []):
        scope = write.get("scope")
        key = write.get("key")
        if not key:
            add_error(state, step, "memory write without key")
            continue
        if scope == "shared":
            if key in state.shared_memory:
                add_error(state, step, f"shared memory key '{key}' already exists")
                continue
            state.shared_memory[key] = {
                "event": event.get("event"),
                "agent": event.get("agent"),
                "tool": event.get("tool"),
                "step": step,
                "trace": trace_id,
                "value": write.get("value"),
            }
            state.counters["memory_writes"] += 1
        elif scope == "local":
            state.counters["memory_writes"] += 1
        else:
            add_error(state, step, f"unsupported memory scope '{scope}'")


def check_tool_call(state: TraceState, step: Any, event: dict[str, Any], rules: dict[str, Any], agents: set[str]) -> None:
    state.counters["tool_calls"] += 1
    agent = event.get("agent")
    tool = event.get("tool")
    if not require_known_agent(state, step, agent, agents, "tool-calling"):
        return
    tools = rules.get("tools", {})
    if tool not in tools:
        add_error(state, step, f"unknown tool '{tool}'")
        return
    spec = tools[tool]
    if agent not in spec.get("allowed_agents", []):
        add_error(state, step, f"agent '{agent}' lacks permission for tool '{tool}'")
    cost = int(spec.get("cost", 0))
    remaining = state.budgets.get(agent, 0)
    if remaining < cost:
        add_error(state, step, f"insufficient budget for '{agent}': required {cost}, available {remaining}")
    else:
        state.budgets[agent] = remaining - cost
        state.counters["budget_consumed"] += cost
    record_writes(state, step, event)


def check_handoff(state: TraceState, step: Any, event: dict[str, Any], rules: dict[str, Any], agents: set[str]) -> None:
    state.counters["handoffs"] += 1
    source = event.get("from")
    target = event.get("to")
    ok_source = require_known_agent(state, step, source, agents, "source")
    ok_target = require_known_agent(state, step, target, agents, "target")
    if ok_source and ok_target and not allowed_edge(rules, source, target):
        add_error(state, step, f"handoff edge '{source} -> {target}' is not allowed")
    if not payload_allowed(rules, "handoff", event):
        add_error(state, step, "handoff payload violates configured policy")


def check_message(state: TraceState, step: Any, event: dict[str, Any], rules: dict[str, Any], agents: set[str]) -> None:
    state.counters["messages"] += 1
    source = event.get("from")
    target = event.get("to")
    ok_source = require_known_agent(state, step, source, agents, "source")
    ok_target = require_known_agent(state, step, target, agents, "target")
    if ok_source and ok_target and not allowed_edge(rules, source, target):
        add_error(state, step, f"message edge '{source} -> {target}' is not allowed")
    if not payload_allowed(rules, "message", event):
        add_error(state, step, "message payload violates configured policy")


def check_certify(state: TraceState, step: Any, event: dict[str, Any], rules: dict[str, Any], agents: set[str]) -> None:
    agent = event.get("agent")
    if not require_known_agent(state, step, agent, agents, "certifying"):
        return
    if agent not in set(rules.get("certifiers", [])):
        add_error(state, step, f"agent '{agent}' is not authorised to certify claims")
    claim = event.get("claim")
    source = event.get("source")
    if not claim:
        add_error(state, step, "certificate without claim")
    if not source:
        add_error(state, step, "certificate without source")
    elif source not in state.shared_memory:
        add_error(state, step, f"certificate source '{source}' not found in shared memory")
    if claim and source in state.shared_memory:
        state.certified_claims.add((claim, source))
        state.counters["certificates"] += 1


def check_answer(state: TraceState, step: Any, event: dict[str, Any], agents: set[str]) -> None:
    agent = event.get("agent")
    require_known_agent(state, step, agent, agents, "answering")
    state.counters["answers"] += 1
    certified_claim_names = {claim for claim, _source in state.certified_claims}
    for claim in event.get("claims", []):
        if claim not in certified_claim_names:
            add_error(state, step, f"answer uses uncertified claim '{claim}'")


def check_memory_update(state: TraceState, step: Any, event: dict[str, Any], agents: set[str]) -> None:
    agent = event.get("agent")
    if not require_known_agent(state, step, agent, agents, "memory-writing"):
        return
    record_writes(state, step, event)


def check_trace(trace: list[dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    agents = set(rules.get("agents", []))
    required_events = set(rules.get("trace_required_for", []))
    state = TraceState(budgets=dict(rules.get("initial_budgets", {})))

    for index, event in enumerate(trace, start=1):
        step = event.get("step", index)
        state.counters["events"] += 1
        budgets_before = dict(state.budgets)
        memory_before = copy.deepcopy(state.shared_memory)
        claims_before = set(state.certified_claims)
        traces_before = set(state.traces)
        counters_before = dict(state.counters)
        error_count_before = len(state.errors)
        if step != index:
            add_error(state, step, f"non-sequential step number, expected {index}")
        event_type = event.get("event")
        require_trace(state, step, event, required_events)

        if event_type == "tool_call":
            check_tool_call(state, step, event, rules, agents)
        elif event_type == "handoff":
            check_handoff(state, step, event, rules, agents)
        elif event_type == "message":
            check_message(state, step, event, rules, agents)
        elif event_type == "certify":
            check_certify(state, step, event, rules, agents)
        elif event_type == "answer":
            check_answer(state, step, event, agents)
        elif event_type == "shared_memory_update":
            check_memory_update(state, step, event, agents)
        else:
            add_error(state, step, f"unknown event type '{event_type}'")

        if len(state.errors) > error_count_before:
            state.budgets = budgets_before
            state.shared_memory = memory_before
            state.certified_claims = claims_before
            state.traces = traces_before
            state.counters = counters_before

    return {
        "accepted": not state.errors,
        "errors": state.errors,
        "final_budgets": state.budgets,
        "shared_memory": sorted(state.shared_memory),
        "shared_provenance": state.shared_memory,
        "certified_claims": sorted({claim for claim, _source in state.certified_claims}),
        "certified_claim_sources": [
            {"claim": claim, "source": source}
            for claim, source in sorted(state.certified_claims)
        ],
        "counters": state.counters,
    }


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
    rejected_diagnostics = "\n".join(
        error
        for result in rejected
        for error in result.get("errors", [])
    )
    accepted_framework_styles = sorted({
        style
        for result in accepted
        for style in result.get("framework_styles", [])
    })

    obligations = {
        "known_participating_agents": {
            "positive": bool(accepted),
            "negative": "unknown" in rejected_diagnostics,
        },
        "graph_edges_for_handoffs_messages": {
            "positive": any({"handoff", "message"} & set(result.get("event_types", [])) for result in accepted),
            "negative": "edge" in rejected_diagnostics,
        },
        "handoff_message_payload_policy": {
            "positive": any({"handoff", "message"} & set(result.get("event_types", [])) for result in accepted),
            "negative": "payload violates" in rejected_diagnostics,
        },
        "tool_permission_and_known_tools": {
            "positive": "tool_call" in accepted_event_types,
            "negative": "lacks permission" in rejected_diagnostics or "unknown tool" in rejected_diagnostics,
        },
        "linear_budget_consumption": {
            "positive": any(result["counters"].get("budget_consumed", 0) > 0 for result in accepted),
            "negative": "insufficient budget" in rejected_diagnostics,
        },
        "append_only_shared_memory": {
            "positive": any(result["counters"].get("memory_writes", 0) > 0 for result in accepted),
            "negative": "already exists" in rejected_diagnostics or "unsupported memory scope" in rejected_diagnostics,
        },
        "fresh_audit_evidence": {
            "positive": all(result["counters"].get("trace_items", 0) > 0 for result in accepted),
            "negative": "lacks required audit trace" in rejected_diagnostics or "duplicate trace" in rejected_diagnostics,
        },
        "claim_source_certification": {
            "positive": any(result["counters"].get("certificates", 0) > 0 for result in accepted),
            "negative": "certificate source" in rejected_diagnostics or "not authorised" in rejected_diagnostics,
        },
        "answer_cites_certified_claims": {
            "positive": any(result["counters"].get("answers", 0) > 0 for result in accepted),
            "negative": "uncertified claim" in rejected_diagnostics,
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
        result["trace"] = trace_path.name
        result["event_types"] = sorted({event.get("event", "") for event in trace})
        result["framework_styles"] = sorted({
            event.get("framework", {}).get("style")
            for event in trace
            if isinstance(event.get("framework"), dict) and event.get("framework", {}).get("style")
        })
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
