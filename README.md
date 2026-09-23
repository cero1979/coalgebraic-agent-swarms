# Anonymous replication package

This repository accompanies the manuscript **Resource-Sensitive Certification of
Tool-Augmented Agent Swarms: Coalgebraic Semantics and LangGraph Validation**.
It contains the anonymous editable
manuscript, its supporting software, original synthetic validation data, and the
recorded results supplied for peer review.

Anonymous reviewer access:
<ANONYMOUS_REVIEW_REPOSITORY>.

The experiments use deterministic local tools. No model API, credentials, cloud
service, human participant data, or external dataset is required. The checker
validates the stated structural and resource policies; it does not establish the
factual truth of tool outputs.

## Contents

- `main.tex`, `references.bib`, and the flat LaTeX dependencies: editable anonymous
  manuscript. `make paper` builds `main.pdf` from these editable sources.
- `prototype/`: checker, rules, 19 conformance traces, 26 unit tests, and supplied
  checker outputs.
- `integrations/langgraph/`: three deterministic LangGraph workflows, canonical
  trace adapter, and five integration tests.
- `experiments/`: E1--E4 runner, mutation and scaling generators, 14 experiment
  tests, supplied JSON/CSV results, and their integrity manifest.
- `paper/generated/`: the four generated evaluation tables. Flat copies beside
  `main.tex` support submission systems that flatten LaTeX uploads.
- `LICENSE_REVIEW.txt` and `DATA_LICENSE_REVIEW.txt`: software and data licenses
  with author attribution withheld for anonymous review.

## Setup

Use Python 3.12 and the pinned dependency versions:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Compiling the manuscript also requires a LaTeX distribution with `pdflatex`,
`bibtex`, and `latexmk`.

## Check the supplied results

Run the research tests and verify both SHA-256 manifests before regenerating any
results:

```sh
make test
make verify
make paper
```

The test suite contains 45 tests. The supplied E1 results cover 19 traces (five
accepted positive controls and 14 rejected negative controls). E2 records three
accepted framework workflows. E3 detects all 42 targeted mutations with the
expected rejection code and step. E4 measures communication-only traces from 10
to 10,000 events with one warmup and seven timed repetitions per size. These are
bounded validation results, not estimates of performance on arbitrary agent
deployments.

`make paper` compiles the supplied tables without rerunning the experiments.
`make check` runs tests, verifies the supplied evidence, and compiles the paper.

## Regenerate the experiments

```sh
make all
```

This reruns E1--E4 and the checker trace suite, refreshes their manifests, copies
the new evaluation tables to the flat LaTeX filenames, and compiles the paper.
It replaces the supplied result files in this checkout. Native framework task
IDs, timestamps, environment metadata, and measured runtimes can change between
runs; canonical event counts, conformance outcomes, and mutation labels are
deterministic. New timings describe the reviewer's machine and environment.
`make reproduce` is an equivalent explicit target.

Individual targets are available through `make help`. Further methodology and
command-line options are documented in `experiments/README.md`,
`prototype/README.md`, and `integrations/langgraph/README.md`.

Author identities, public repository coordinates, and the original Git history
are withheld from this reviewer snapshot. The supplied environment record keeps
the measurement platform and dependency versions while withholding the original
branch and commit identifiers.
