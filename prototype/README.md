# Prototype Trace Checker

This directory contains a lightweight executable artefact for the paper
"A Coalgebraic and Resource-Sensitive Semantics for Tool-Augmented Agent Swarms".

## Purpose

The checker validates JSON execution traces of a multi-agent swarm against a
SELL-inspired resource discipline. It checks:

- known agents;
- allowed handoff/message edges;
- configured handoff/message payload policies;
- tool permissions;
- linear budget consumption;
- append-only shared-memory writes with provenance;
- claim certification from shared sources, retaining claim-source pairs;
- audit-trace obligations for tool calls, handoffs, messages, shared-memory updates, certifications, and answers.

The checker is not a full SELL prover. It recognises the side-conditioned
certificate schemas used in the article. The suite contains 19 traces: 5
accepted conformance scenarios and 14 rejected negative controls.

Every write with `"scope": "shared"` must contain a non-empty explicit
`"provenance"` value. The checker preserves that value verbatim in the
corresponding `shared_provenance` record; event metadata does not substitute for
source provenance.

## Result and violation schema

`check_trace(trace, rules)` retains the original result fields and additionally
returns a `violations` list. Each item has a stable machine-readable code and a
separate human-readable message:

```json
{
  "code": "tool_permission",
  "step": 3,
  "message": "agent 'Planner' lacks permission for tool 'BibliographicSearch'"
}
```

The corresponding legacy `errors` item remains
`"step 3: agent 'Planner' lacks permission ..."`. Stable experiment-facing
codes include `unknown_agent`, `unknown_tool`, `tool_permission`,
`insufficient_budget`, `illegal_handoff`, `illegal_message`, `payload_policy`,
`missing_provenance`, `certificate_source`, `unauthorized_certifier`,
`duplicate_audit`, `missing_audit`, `memory_overwrite`, `uncertified_claim`,
`unknown_event`, and `nonsequential_step`.

Malformed structural fields are also rejected without aborting the checker.
Their diagnostic codes are `memory_scope`, `invalid_writes`, `invalid_write`,
`missing_memory_key`, `invalid_claims`, and `missing_claim`. In particular, a
`shared_memory_update` must contain at least one write, event objects and their
identifiers must have the expected JSON types, and `step` must be a strict JSON
integer (booleans and floating-point values are rejected).

## Transaction and complexity model

Rules are indexed once per `check_trace` call into sets and dictionaries for
agents, graph edges, tools, permissions, certifiers, and audit requirements.
Each event is validated into a pending plan. Budget debits, audit identifiers,
memory writes, counters, and certificates are committed only when the complete
event is valid. Rejected events therefore leave no partial ledger effects and
do not require copying the accumulated ledger.

Under the standard constant-time indexed-lookup model, the worst-case input
traversal and result construction take `O(S + N)` time and `O(S + N)` space,
where `S` is the finite rule specification size and `N` includes events,
claims, writes, and provenance payloads. No per-event deep copy of prior memory,
claims, or audit state occurs.

## Files

- `checker.py`: trace checker implementation.
- `test_checker.py`: conformance and rejected-event transaction tests.
- `verify_manifest.py`: SHA-256 manifest verifier.
- `rules.json`: swarm graph, payload policies, tools, permissions, budgets, and trace rules.
- `traces/valid_research_swarm.json`: accepted research-assistant trace.
- `traces/valid_two_source_research_swarm.json`: accepted two-source trace.
- `traces/valid_memory_update_reuse_trace.json`: accepted shared-memory-update trace.
- `traces/valid_claim_reuse_trace.json`: accepted trace showing reusable certified claims with fresh answer traces.
- `traces/valid_langgraph_like_trace.json`: accepted LangGraph-like normalised trace carrying framework metadata.
- `traces/invalid_bad_memory_scope.json`: rejected unsupported memory scope.
- `traces/invalid_budget_violation.json`: rejected budget violation.
- `traces/invalid_certificate_source.json`: rejected unsupported certificate.
- `traces/invalid_duplicate_trace.json`: rejected duplicate trace identifier.
- `traces/invalid_handoff_violation.json`: rejected graph violation.
- `traces/invalid_message_violation.json`: rejected message graph violation.
- `traces/invalid_missing_trace.json`: rejected audit-trace violation.
- `traces/invalid_payload_policy.json`: rejected payload-policy violation.
- `traces/invalid_shared_memory_overwrite.json`: rejected shared-memory overwrite.
- `traces/invalid_tool_permission.json`: rejected tool-permission violation.
- `traces/invalid_unauthorized_certifier.json`: rejected certification by an unauthorised agent.
- `traces/invalid_uncertified_answer.json`: rejected uncertified answer.
- `traces/invalid_unknown_agent.json`: rejected event involving an unknown agent.
- `traces/invalid_unknown_tool.json`: rejected call to an unknown tool.
- `results/results.json`: machine-readable per-trace results.
- `results/results.csv`: tabular per-trace results.
- `results/results_table.tex`: LaTeX results table included by `main.tex`.
- `results/coverage_summary.json`: aggregate conformance and obligation-coverage summary.
- `results/coverage_table.tex`: LaTeX coverage table included by `main.tex`.
- `results/MANIFEST.json`: SHA-256 manifest for checker, rules, traces, and generated outputs.

## Reproduce

Run from the project root:

```bash
python3 prototype/checker.py --rules prototype/rules.json --traces prototype/traces/*.json --out-dir prototype/results
python3 prototype/verify_manifest.py prototype/results/MANIFEST.json
```

Then compile the paper:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```
