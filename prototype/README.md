# Prototype Trace Checker

This directory contains a lightweight executable artefact for the paper
"A Coalgebraic and Resource-Sensitive Semantics for Tool-Augmented Agent Swarms".

## Purpose

The checker validates JSON execution traces of a multi-agent swarm against a
SELL-inspired resource discipline. It checks:

- known agents;
- allowed handoff/message edges;
- tool permissions;
- linear budget consumption;
- append-only shared-memory writes with provenance;
- claim certification from shared sources, retaining claim-source pairs;
- audit-trace obligations for tool calls, handoffs, messages, shared-memory updates, certifications, and answers.

The checker is not a full SELL prover. It is an executable abstraction of the
resource discipline used in the article. The current suite contains 18 traces:
5 accepted conformance scenarios and 13 rejected negative controls.

## Files

- `checker.py`: trace checker implementation.
- `rules.json`: swarm graph, tools, permissions, budgets, and trace rules.
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
```

Then compile the paper:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```