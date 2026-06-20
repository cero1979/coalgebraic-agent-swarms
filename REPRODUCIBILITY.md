# Reproducibility Guide

This document explains how to reproduce the article artefacts from a clean checkout.
The resubmission snapshot is tagged `jlamp-resubmission-2026-06`.

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

The generated LaTeX tables are included by `main.tex`. Generated summaries do
not contain runtime-version fields, so they are byte-stable across supported
Python versions.

## 2. Verify the Manifest

Run:

```bash
python3 prototype/verify_manifest.py prototype/results/MANIFEST.json
```

Equivalent Make target:

```bash
make verify
```

The verifier checks the manuscript source, LaTeX class files, checker, rules,
traces, and generated results against their recorded SHA-256 values.

## 3. Compile the Paper

Run:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Equivalent Make target:

```bash
make paper
```

The expected output is `main.pdf`.

## 4. Clean Build Artefacts

Run:

```bash
make clean
```

This removes common LaTeX auxiliary files while leaving source files, prototype traces, results, and the PDF intact.

## 5. Conformance Suite Summary

The trace suite is intentionally finite and hand-checkable. It contains 19
traces: 5 accepted conformance scenarios and 14 rejected negative controls.

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
- `prototype/traces/invalid_payload_policy.json`
- `prototype/traces/invalid_shared_memory_overwrite.json`
- `prototype/traces/invalid_tool_permission.json`
- `prototype/traces/invalid_unauthorized_certifier.json`
- `prototype/traces/invalid_uncertified_answer.json`
- `prototype/traces/invalid_unknown_agent.json`
- `prototype/traces/invalid_unknown_tool.json`

## 6. Interpretation

Accepted traces instantiate the implemented local-soundness obligations of the
paper. Rejected traces are negative controls for graph, payload policy,
permission, budget, provenance, certification, and audit failures.
