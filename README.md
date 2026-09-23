# Resource-Sensitive Certification of Tool-Augmented Agent Swarms

**Repository:** <https://github.com/cero1979/coalgebraic-agent-swarms>

This repository contains the editable manuscript and reproducibility artefact
for the Regular Paper prepared for *Array*:

> **Resource-Sensitive Certification of Tool-Augmented Agent Swarms: Coalgebraic
> Semantics and LangGraph Validation**

The artefact separates a framework execution trace from a resource-certified
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

The machine-readable outputs in this revised checkout report four distinct
evaluation groups:

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

The original synthetic records under `prototype/` and `experiments/results/`
are released under CC BY 4.0 as specified in `DATA_LICENSE.md`; the software is
released under the MIT licence in `LICENSE`.

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
|-- DATA_LICENSE.md                   # CC BY 4.0 scope for synthetic data
|-- LICENSE                           # Software licence
`-- Makefile                          # Reproducibility entry points
```

## Reproduce

Python 3.12 is the reference interpreter. To reproduce the revised manuscript,
clone the current default branch and record its commit before running the
pipeline:

```bash
git clone https://github.com/cero1979/coalgebraic-agent-swarms.git
cd coalgebraic-agent-swarms
git rev-parse HEAD
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
manifests. `make paper` builds the identified `main.pdf`.
`make submission` builds an anonymous, flat Array package plus the separated
Editorial Manager files under `output/submission/`, including an editable Word
title page; `make submission-check` validates anonymity, dependency paths,
checksums, and isolated compilation. See
`REPRODUCIBILITY.md` for prerequisites, individual experiment targets, and
interpretation limits.

## Versioned Release

The immutable GitHub release
[`v1.0.0`](https://github.com/cero1979/coalgebraic-agent-swarms/releases/tag/v1.0.0)
is a historical baseline, not the revised submission or its current E1-E4
result files. Its PDF, data archive, SHA-256 inventory, and source archives
remain available for comparison. Use the commit recorded from the current
default branch, together with this checkout's manifests, to identify the
revised source and results. E4 wall-clock measurements may change when rerun.

Because the live submission portal requests a manuscript without author
identifiers, the local upload builder produces a separate anonymous review copy
and an anonymous supplementary archive. These review-only files do not replace
or alter the identified public repository or its historical release. A new
anonymous mirror must be generated from the revised state and verified without
sign-in for both accessibility and author-identity leaks before its URL is
used in reviewer-facing material; the earlier mirror is not a valid reference
for this revision. The local anonymous supplement is available independently
of a remote mirror.

No archival DOI has been assigned. The historical release has no DOI, and the
revised manuscript identifies its artifact without inventing one. A future
Zenodo deposit would improve long-term FAIR discovery but is not represented as
already existing.
