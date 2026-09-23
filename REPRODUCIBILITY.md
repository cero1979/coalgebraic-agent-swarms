# Reproducibility Guide

This guide reproduces the software tests, four evaluation groups, and manuscript
from a clean checkout of the revised default branch. The separate flat
*Array* submission package also requires identified editorial files kept
locally by the author. Record the checked-out commit: the older immutable public
release `v1.0.0` is a historical baseline, not the source of this revision's
tables and timing data.

## 1. Prerequisites

- Python 3.12 and `venv`/`pip`;
- `make`;
- a LaTeX distribution providing `latexmk`, pdfLaTeX, BibTeX, and `kpsewhich`
  for the paper and flat submission package;
- sufficient local disk space for the pinned Python environment.

Clone the revised default branch, record its commit, create the reference
environment, and install the pinned dependencies:

```bash
git clone https://github.com/cero1979/coalgebraic-agent-swarms.git
cd coalgebraic-agent-swarms
git rev-parse HEAD
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Dependency installation may contact the configured Python package index. Once
installed, the tests and experiments run locally without a model API, API key,
commercial service, dataset download, or network call.

The recorded experiment environment is CPython 3.12.10 with LangGraph 1.2.11
and `langchain-core` 1.5.4. The recorded E4 measurements were collected in an
x86_64 translated process on an arm64 Apple M3 Pro running macOS 27.0. Exact
timings are platform-dependent.

## 2. End-to-End Reproduction

Run the complete public research pipeline from the repository root:

```bash
make all
```

This runs the test suites, regenerates the original prototype outputs,
regenerates E1-E4 and their manuscript tables, verifies both manifests, and
compiles the manuscript. It does not require identified author files.

The same stages can be run explicitly:

```bash
make test
make experiments
make verify
make paper
```

The two editorial targets below are run separately on the author's local
checkout after supplying the identified title-page and cover-letter files and
an ignored `.anonymous-review-url` file containing the verified anonymous
review URL on one line:

```bash
make submission
make submission-check
```

Use `make help` for the current target descriptions.

## 3. Tests

```bash
make test
```

This discovers the unit tests under `prototype/`,
`integrations/langgraph/tests/`, `experiments/tests/`, and `scripts/tests/`.
The tests cover checker obligations and transaction behavior, native-to-
canonical adaptation, actual workflow execution, mutation generation, scaling
trace generation, result/manifest production, and submission tooling.

## 4. Evaluation Groups

Regenerate all reported results and manuscript tables:

```bash
make experiments
```

The groups can also be run separately while developing:

```bash
make conformance
make framework
make mutations
make benchmark
```

A partial run invalidates the complete experiment manifest. Run
`make experiments` afterward before `make verify` or before freezing a release.

### E1: conformance

E1 runs all 19 committed handcrafted synthetic traces. The expected result is
19/19 expectation matches: 5 accepted traces and 14 rejected controls, 55
events in total. The negative controls target graph, payload, permission,
budget, certificate-source, certifier, claim-support, memory, identity, tool,
and audit failures.

`make prototype-results` separately regenerates the legacy per-trace files
under `prototype/results/`; `make results` is a backward-compatible alias.

### E2: framework validation

E2 executes three actual deterministic LangGraph 1.2.11 `StateGraph`
workflows: `research`, `resource_controlled`, and `shared_memory`. The expected
result is 3/3 accepted framework traces, with 63 captured native records and 23
canonical checker events in the recorded run.

The native stream retains LangGraph v2 `tasks`, `updates`, and `values`
records. The adapter maps explicit application emissions to canonical events.
Permissions, SELL costs, factual truth, and provenance for uninstrumented
effects are not supplied by LangGraph and are not inferred by the adapter.

### E3: mutation testing

E3 applies 14 controlled violation categories to each of the three E2
canonical traces. The expected result is 42/42 strict detections: every mutant
is rejected at the changed step with exactly the expected violation code.

This measures detection of known, seeded faults derived from the same three
valid traces. It is not an estimate of attack coverage, false-positive rate,
or effectiveness against adaptive adversaries.

### E4: implementation scaling

E4 checks accepted synthetic traces of 10, 100, 1,000, 5,000, and 10,000
events. Each trace alternates permitted `message` and `handoff` events and uses
unique audit identifiers. The default protocol performs one warmup and seven
measured repetitions per length using `time.perf_counter_ns`.

Timing covers one `check_trace` call, including rule indexing. Preparation of
deep-copied inputs occurs outside the timed region. These communication-only
traces do not represent the full event mix, model inference, framework
execution, network latency, or production deployment.

## 5. Generated Outputs

`make experiments` writes:

- `experiments/results/conformance_results.{json,csv}`;
- `experiments/results/framework_runs.{json,csv}`;
- `experiments/results/mutation_results.{json,csv}`;
- `experiments/results/runtime_results.{json,csv}`;
- `experiments/results/summary.json`;
- `experiments/results/environment.json`;
- `experiments/results/MANIFEST.json`;
- `paper/generated/conformance_table.tex`;
- `paper/generated/framework_validation_table.tex`;
- `paper/generated/mutation_table.tex`;
- `paper/generated/runtime_table.tex`.

The numeric manuscript tables are generated from these machine-readable
outputs. Native framework task identifiers and wall-clock timings can vary
between runs; outcome counts, canonical event counts, mutation definitions,
and table structure are deterministic for the pinned code and inputs.

## 6. Data Provenance

Every evaluation input and output is original synthetic/generated research
data produced for this study. E1 uses hand-authored fixtures; E2 uses records
emitted by deterministic local workflows; E3 generates controlled mutants;
and E4 generates communication-only traces. There are no human subjects,
personal records, third-party datasets, downloaded benchmark corpora, or
language-model outputs. Bibliographic-looking values inside workflow fixtures
are illustrative strings, not data collected from publications.

Suggested data-source metadata:

- **Classification:** Original data
- **Title:** Coalgebraic Agent Swarms: Conformance Traces and LangGraph
  Validation Outputs

The original synthetic inputs, outputs, and generated result tables are
licensed under CC BY 4.0 as scoped in `DATA_LICENSE.md`. Software remains under
the MIT licence in `LICENSE`.

## 7. Integrity Verification

```bash
make verify
```

This checks `prototype/results/MANIFEST.json` and
`experiments/results/MANIFEST.json` against the current source inputs and
generated outputs using SHA-256. A successful check establishes internal
snapshot integrity; it does not by itself create a public or immutable archive.

If source files or results have intentionally changed, regenerate the
corresponding artefacts first:

```bash
make prototype-results
make experiments
make verify
```

## 8. Paper and Submission Package

Compile the editable manuscript:

```bash
make paper
```

The expected output is `main.pdf`. Build the local flat Editorial Manager
package with:

```bash
make submission
```

Run the objective checks and an isolated compilation with:

```bash
make submission-check
```

These editorial targets require local `title_page.tex` and `title_page.docx`
files, the identified `submission/array/cover_letter.tex`, and the ignored
`.anonymous-review-url` file. They are not required by the public `make all`
target or the continuous-integration check.
The generated `submission/array/` directory is a local staging artefact. The
portal-ready files are under `output/submission/`: a flat anonymous LaTeX source
ZIP, anonymous manuscript preview, separate identified editable Word title
page (with LaTeX source and PDF preview), confidential cover letter, highlights,
anonymous supplementary archive, instructions, and SHA-256 inventory. Do not
upload the complete staging directory as a single
manuscript item because it deliberately contains both anonymous and identified
documents.

The validator rejects nested LaTeX dependency references and direct author
identifiers in the review manuscript. It compiles the anonymous manuscript,
title page, and cover letter independently in a fresh directory. The anonymous
supplement removes repository commit/branch identifiers and refreshes both
integrity manifests after that transformation.

The local anonymous supplement provides reviewer access to the revised code,
synthetic inputs, and results without relying on a remote mirror. The
author-side editorial builder requires the local review URL and cites both the
pinned, sanitised mirror and the supplementary archive. A public clone can run
`make all` without this configuration but cannot build the editorial package.
The mirror excludes identity, editorial, and repository-history files and is not
auto-updated. Before changing its snapshot or URL, repeat signed-out access,
direct/indirect identity, integrity, and version-match checks. Its URL must
not be committed to the identified public repository. Direct-identifier
removal cannot guarantee unlinkability from older public work.

## 9. Release Integrity

Release `v1.0.0` is a historical public baseline, not the revised manuscript or
current experiment outputs. GitHub's immutable release retains its original
tag and assets and provides a signed release attestation. The attached
`SHA256SUMS-v1.0.0.txt` records the manuscript and dataset-archive hashes.

The release contains:

- `array-manuscript-v1.0.0.pdf`;
- `coalgebraic-agent-swarms-data-v1.0.0.zip`; and
- `SHA256SUMS-v1.0.0.txt`.

GitHub supplies source-code ZIP and TAR archives directly from the tagged
commit. For the revised work, record the current commit and verify the
manifests generated from that checkout. No Zenodo record or DOI is claimed. If
an archival DOI is assigned later, it must be added in a new, internally
consistent version rather than retroactively asserted for `v1.0.0`.

## 10. Cleaning Local Build Files

```bash
make clean
```

This removes Python caches and common LaTeX auxiliary files while retaining
source files, experiment results, and final PDFs.
