# A Coalgebraic and Resource-Sensitive Semantics for Tool-Augmented Agent Swarms

**Repository:** <https://github.com/cero1979/coalgebraic-agent-swarms>

This repository contains the manuscript and reproducibility artefact for the paper:

> **A Coalgebraic and Resource-Sensitive Semantics for Tool-Augmented Agent Swarms**

The paper proposes a formal semantics for tool-augmented agent swarms. Coalgebra models observable state-based dynamics; a SELL-labelled certification layer controls resources such as tool permissions, budgets, memory, provenance, and audit traces. The repository also includes a small executable trace checker and a conformance suite of positive and negative traces.

## Repository Layout

```text
.
├── main.tex                         # Article source
├── main.pdf                         # Compiled article PDF, if generated locally
├── Makefile                         # Reproducibility commands
├── REPRODUCIBILITY.md               # Detailed artefact instructions
└── prototype/
    ├── README.md                    # Prototype-specific documentation
    ├── checker.py                   # JSON trace checker
    ├── rules.json                   # Finite swarm specification
    ├── traces/                      # Accepted and rejected example traces
    └── results/                     # Generated tables, summaries, and manifest
```

## Main Claims Implemented in the Artefact

The prototype validates finite JSON traces against the implemented fragment of the paper's certification discipline. It checks:

- known participating agents;
- allowed handoff and message edges;
- tool permissions and known tools;
- linear budget consumption;
- append-only shared-memory writes with provenance;
- claim certification from shared source keys;
- final answers citing only certified claims;
- fresh audit traces for auditable events.

The current conformance suite contains 18 traces: 5 accepted traces and 13 rejected traces covering targeted violations. The accepted set now includes a shared-memory update trace, a reusable-claim trace, and a LangGraph-like normalised trace with framework metadata.

## Quick Reproduction

Clone and run the checker:

```bash
git clone https://github.com/cero1979/coalgebraic-agent-swarms.git
cd coalgebraic-agent-swarms
python3 prototype/checker.py \
  --rules prototype/rules.json \
  --traces prototype/traces/*.json \
  --out-dir prototype/results
```

Or use the Make targets:

```bash
make results   # regenerate prototype results
make paper     # compile the article PDF (requires latexmk)
make all       # both steps
```

## Expected Results

The checker should accept:

- `valid_research_swarm.json`
- `valid_two_source_research_swarm.json`
- `valid_memory_update_reuse_trace.json`
- `valid_claim_reuse_trace.json`
- `valid_langgraph_like_trace.json`

It should reject the remaining traces, including violations of budget, graph topology, tool permission, certificate source support, duplicate traces, missing traces, memory overwrite, unknown agents, unknown tools, and unauthorised certifiers. It also writes `coverage_summary.json`, `coverage_table.tex`, and `MANIFEST.json` with SHA-256 checksums for reproducibility.

## Requirements

- Python 3.10+ recommended.
- A LaTeX installation with `latexmk` for building the PDF.
- No external Python packages are required by the checker.

## Notes

The checker is intentionally small. It is not a full SELL proof-search implementation; it is an executable recogniser for the finite certificate fragment described in the paper.