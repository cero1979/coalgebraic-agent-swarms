# Array Revision Notes

This internal log records the scientific audit, revision decisions, completed
evidence, and remaining submission gates for the *Array* Regular Paper. It is
not itself a submission document.

## Working State

- Release tag: `v1.0.0`
- Release URL: <https://github.com/cero1979/coalgebraic-agent-swarms/releases/tag/v1.0.0>
- Article type: Regular Paper
- Manuscript source: `main.tex`
- Reproducibility entry point: `make all`
- Public-release status: immutable GitHub release with signed attestation and
  checksummed assets; no archival DOI is claimed

The editable manuscript was preserved on a dedicated branch before the
revision began. Release `v1.0.0` is the authoritative software/data snapshot
for the submission. GitHub release immutability prevents its tag and assets
from being changed after publication.

## Scientific Audit and Decisions

### Relationship between coalgebra and SELL

The revision no longer presents the two formalisms as a universal or deeply
integrated new calculus. Coalgebra supplies the deterministic observable event
semantics; the side-conditioned SELL-labelled ledger admits or rejects the
resulting events. Their concrete point of contact is the canonical event and
certificate interface implemented by the checker.

The manuscript now states that the checker recognises a fixed six-rule
fragment. It does not claim complete SELL proof search, focusing completeness,
general cut consequences, or a mechanised correspondence theorem.

### Coalgebraic scope

The coalgebraic model is intentionally restricted to deterministic
Moore/Mealy-style behavior. Standard final-semantics and bisimulation facts
are treated as background rather than technical novelty. The contribution is
the separation between raw framework behavior and resource-certified finite
runs, together with the executable validation boundary.

### Composition and accessibility

Unsupported shared-interface composition claims were removed. The surviving
composition statement is limited to disjoint interleavings under explicit
hypotheses. Direct graph edges are checked operationally for messages and
handoffs. The reflexive-transitive agent-zone preorder is retained only as an
explicit extension point; the current six schemas and checker do not use it as
a general SELL accessibility theorem.

### Checker correspondence and complexity

The checker was refactored around validate-then-commit transitions and indexed
rules. Claims now follow the implemented event schemas, including their
JSON-admissible surface predicates, and account for the full specification
size. The preservation statements assume a source-well-formed initial ledger.
Empirical timing is reported separately from the expected-time word-RAM
argument and is not treated as a proof of production scalability.

### Prior-work positioning

The comparison now distinguishes the artefact from process algebra and session
types, live specification enforcement, least-privilege tool guards,
information-flow control, provenance capture, and agent-security benchmarks.
The manuscript does not claim superiority over those systems. In particular,
the present implementation is a deterministic trace validator, not a live
pre-tool-call enforcement layer and not a non-interference proof.

## Implemented Evidence

### Software

- The checker validates all event fields before committing a transition and
  reports structured violation codes.
- The LangGraph adapter executes three real version-pinned `StateGraph`
  workflows and retains native v2 `tasks`, `updates`, and `values` streams.
- Domain events are emitted by deterministic application instrumentation and
  normalized only after framework execution.
- Test suites cover checker behavior, integration behavior, experiment
  generation, manifest tamper detection, and submission tooling.
- The repository includes exact Python dependencies, a licence, citation
  metadata, and automated build/validation entry points.

### Evaluation

| Group | Current result | Interpretation limit |
|---|---|---|
| E1 | 19/19 expected outcomes; 5 accepted, 14 rejected; 55 events | Finite handcrafted synthetic suite |
| E2 | 3/3 LangGraph 1.2.11 workflows accepted; 63 native records, 23 canonical events | Three deterministic local workflows in one framework |
| E3 | 42/42 strict detections; 14 categories applied to three source traces | Seeded known faults, not adaptive security evaluation |
| E4 | 10--10,000 communication-only events; one warmup plus seven measurements | Platform-dependent checker timing for a restricted event mix |

All evaluation data are original synthetic or generated for this study. No
human, personal, or third-party dataset is used. The framework executions use
deterministic Python functions without a language model, commercial API,
credential, external service, or network call.

## Claims Explicitly Excluded

The revision does not claim:

- factual correctness or trustworthiness of a tool result;
- authenticated provenance for effects outside explicit instrumentation;
- resistance to prompt injection or adaptive adversaries;
- protocol fidelity, liveness, fairness, or termination;
- complete SELL proof search or mechanised soundness;
- general shared-state compositionality;
- validation beyond the three included LangGraph workflows;
- production throughput or platform-independent timing; or
- an archival DOI or Zenodo record for release `v1.0.0`.

## Reproducibility and Submission Gates

Automated gates are exposed through:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make test
make experiments
make verify
make paper
make submission
make submission-check
make all
```

The final frozen-state run must confirm that tests pass, both manifests verify,
the manuscript has no unresolved citations/references, the Array validator
passes, and the flat package compiles in isolation.

## Remaining Manual Actions

- [ ] Perform the author's final scientific and line-by-line manuscript review.
- [ ] Confirm author identity, affiliation, correspondence, CRediT, funding,
      competing-interest, data/software, and generative-AI declarations.
- [x] Visually inspect the final manuscript and cover-letter PDFs.
- [ ] Complete Editorial Manager metadata and the declaration-of-interest form.
- [ ] Review APC or institutional-agreement implications.
- [x] Publish and tag the exact final repository commit as `v1.0.0`.
- [x] Publish versioned manuscript/data assets and their SHA-256 inventory.
- [x] Replace provisional repository citations with exact release/asset URLs.
- [x] Run `make verify` and `make all` from a clean release-candidate checkout.
- [ ] Optionally archive a future version in Zenodo and add its DOI only after
      the identifier genuinely exists.

## Change Log

- 2026-08-14: preserved the latest editable manuscript and completed the
  repository, formal-claims, journal-requirements, and reproducibility audit.
- 2026-08-19: completed the checker refactor, actual LangGraph integration,
  E1--E4 runner, systematic mutation study, scaling protocol, generated
  tables, integrity manifests, and Array-oriented documentation.
- 2026-08-19: recorded the release/DOI step as a mandatory manual gate rather
  than claiming that an immutable public artefact already exists.
- 2026-08-20: published the reconciled repository as immutable release
  `v1.0.0`, attached the manuscript and separately licensed synthetic data,
  and retained the absence of an archival DOI as an explicit limitation.
