# Resource-Sensitive Certification of Tool-Augmented Agent Swarms

**Repository:** <https://github.com/cero1979/coalgebraic-agent-swarms>

This repository contains the editable manuscript and reproducibility artefact
for the Regular Paper prepared for *Array*:

> **Resource-Sensitive Certification of Tool-Augmented Agent Swarms: Coalgebraic
> Semantics and LangGraph Validation**

The revision separates a framework execution trace from a resource-certified
trace. A deterministic coalgebra describes observable event/state evolution;
a fixed, side-conditioned SELL-labelled ledger checks tool permissions, linear
budgets, routing, append-only memory, structural provenance, claim support, and
fresh audit evidence. The executable artefact includes an indexed
validate-then-commit checker, three actual LangGraph `StateGraph` workflows,
systematic mutation tests, and a scaling experiment.

The scope is deliberately narrow. The checker is not a complete SELL proof
searcher, the integration validates captured runs rather than interposing a
live tool-call guard, and a certified trace establishes compliance with the
configured structural policy, not the factual truth or trustworthiness of tool
output.

## Evaluation Snapshot

The committed machine-readable outputs report four distinct evaluation groups:

| Group | Evidence | Result |
|---|---|---:|
| E1: conformance | 19 handcrafted synthetic traces, 55 events | 19/19 expected outcomes: 5 accepted, 14 rejected |
| E2: framework validation | Three deterministic LangGraph 1.2.11 `StateGraph` workflows | 3/3 accepted; 63 native records mapped to 23 canonical events |
| E3: mutation testing | 14 targeted violation categories applied to each E2 trace | 42/42 rejected at the mutated step with exactly the expected code |
| E4: scaling | Accepted communication-only traces from 10 to 10,000 events | One warmup and seven measured repetitions per length |

E4 measures only alternating permitted `message` and `handoff` events with
unique audit identifiers. It is an implementation-scaling measurement, not a
production workload or an empirical proof of asymptotic complexity.

## Data Source

All evaluation data are original synthetic or programmatically generated data
created for this study:

- E1 consists of finite, hand-authored conformance fixtures.
- E2 consists of records emitted by deterministic local LangGraph workflows.
- E3 consists of controlled mutations generated from the three E2 traces.
- E4 consists of generated communication-only traces.

No human-participant data, personal data, benchmark corpus, or third-party
dataset is used. The workflows use deterministic Python functions and require
no language model, commercial API, API key, network call, or external service.
Any bibliographic strings used by a workflow are synthetic fixtures rather
than observations extracted from a published dataset.

For an Elsevier source-of-data form, the appropriate classification is
**Original data**. A suitable dataset title is:

> **Coalgebraic Agent Swarms: Conformance Traces and LangGraph Validation
> Outputs**

## Repository Layout

```text
.
|-- main.tex                         # Editable Array manuscript
|-- references.bib                   # Editable bibliography
|-- cas-sc.cls, cas-common.sty        # Elsevier CAS source dependencies
|-- prototype/                       # Checker, rules, E1 traces, legacy results
|-- integrations/langgraph/          # StateGraph workflows and adapter
|-- experiments/                     # E1-E4 runner, tests, and JSON/CSV outputs
|-- paper/figures/                    # Editable manuscript figures
|-- paper/generated/                  # Tables derived from result files
|-- scripts/                          # Flat-bundle builder and validator
|-- HIGHLIGHTS.md                     # Separate editable submission highlights
|-- CLAIM_EVIDENCE_MATRIX.md          # Claims, evidence, and limitations
|-- REPRODUCIBILITY.md                # End-to-end instructions
|-- ARRAY_REVISION_NOTES.md           # Revision audit and remaining gates
|-- CITATION.cff                      # Citation metadata
|-- LICENSE                           # Software licence
`-- Makefile                          # Reproducibility entry points
```

## Reproduce

Python 3.12 is the reference interpreter. From the repository root:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make test
make experiments
make verify
make paper
make submission
```

The complete pipeline is:

```bash
make all
```

`make experiments` writes JSON/CSV results under `experiments/results/` and
four LaTeX tables under `paper/generated/`. `make verify` checks both SHA-256
manifests. `make paper` builds `main.pdf`. `make submission` builds the local
flat Array package, and `make submission-check` additionally validates and
compiles that package in isolation. See `REPRODUCIBILITY.md` for prerequisites,
individual experiment targets, and interpretation limits.

## Release Status

The working branch is `array-resubmission-2026-08`. There is currently **no
final public Array release and no archival DOI** for this revision. The local
files and branch name must not be represented as an immutable archive. After
the manuscript and artefact are frozen, the author must manually publish the
final repository state, create an immutable release, archive that release in a
suitable repository such as Zenodo, and replace any provisional software/data
citation with the resulting persistent identifier before submission.
