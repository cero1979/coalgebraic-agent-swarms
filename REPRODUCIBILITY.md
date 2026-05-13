# Reproducibility Guide

This document explains how to reproduce the article artefacts from a clean checkout.

## 1. Regenerate Prototype Results

From the repository root, run:

```bash
python3 prototype/checker.py \
  --rules prototype/rules.json \
  --traces prototype/traces/*.json \
  --out-dir prototype/results
```

Equivalent Make target:

```bash
make results
```

This regenerates:

- `prototype/results/results.json`
- `prototype/results/results.csv`
- `prototype/results/results_table.tex`
- `prototype/results/coverage_summary.json`
- `prototype/results/coverage_table.tex`
- `prototype/results/MANIFEST.json`

The generated LaTeX tables are included by `main.tex`. The manifest records SHA-256 checksums for the checker, rules, traces, and generated outputs.

## 2. Compile the Paper

Run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Equivalent Make target:

```bash
make paper
```

The expected output is `main.pdf`.

## 3. Clean Build Artefacts

Run:

```bash
make clean
```

This removes common LaTeX auxiliary files while leaving source files, prototype traces, results, and the PDF intact.

## 4. Conformance Suite Summary

The trace suite is intentionally finite and hand-checkable. It currently contains 18 traces: 5 accepted conformance scenarios and 13 rejected negative controls.

Accepted traces:

- `prototype/traces/valid_research_swarm.json`
- `prototype/traces/valid_two_source_research_swarm.json`
- `prototype/traces/valid_memory_update_reuse_trace.json`
- `prototype/traces/valid_claim_reuse_trace.json`
- `prototype/traces/valid_langgraph_like_trace.json`

Rejected traces:

- `prototype/traces/invalid_bad_memory_scope.json`
- `prototype/traces/invalid_budget_violation.json`
- `prototype/traces/invalid_certificate_source.json`
- `prototype/traces/invalid_duplicate_trace.json`
- `prototype/traces/invalid_handoff_violation.json`
- `prototype/traces/invalid_message_violation.json`
- `prototype/traces/invalid_missing_trace.json`
- `prototype/traces/invalid_shared_memory_overwrite.json`
- `prototype/traces/invalid_tool_permission.json`
- `prototype/traces/invalid_unauthorized_certifier.json`
- `prototype/traces/invalid_uncertified_answer.json`
- `prototype/traces/invalid_unknown_agent.json`
- `prototype/traces/invalid_unknown_tool.json`

## 5. Interpretation

Accepted traces instantiate the implemented local-soundness obligations of the paper. Rejected traces are negative controls for graph, permission, budget, provenance, certification, and audit failures.