# Array Revision Notes

This log records the scientific audit, revision decisions, and completed
evidence for the Regular Paper accepted in *Array*. It is not itself a
submission document or a publisher proof.

## Post-Acceptance Status

As of 6 October 2026, the author has confirmed acceptance in Array. Production
instructions and the article DOI are pending. No acceptance date, publication
date, volume, issue, or DOI is inferred from that report.

The version-matched public research snapshot is
`2296430bbcc24505f7407d61858c75ec0f1c31f8`. Its results and measurement-source
metadata are preserved. Identified production files are prepared locally and
have not been uploaded to the repository or sent to the publisher. The
anonymous review snapshot and the Array review records remain historical
materials, not the production package.

## Working State

- Historical baseline release: `v1.0.0`
- Baseline release URL: <https://github.com/cero1979/coalgebraic-agent-swarms/releases/tag/v1.0.0>
- Article type: Regular Paper
- Manuscript source: `main.tex`
- Reproducibility entry point: `make all`
- Baseline-release status: immutable GitHub release with signed attestation and
  checksummed assets; no archival DOI is claimed

The editable manuscript was preserved on a dedicated branch before the
revision began. Release `v1.0.0` documents an earlier software/data/manuscript
snapshot, not the exact source or generated results of the accepted revision.
The current revision is represented by the revised repository files, regenerated
result manifests, and the submission bundle produced from them. GitHub release
immutability prevents the historical tag and assets from being changed after
publication; a new public revision must not be described as that old release.

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
- an archival DOI or Zenodo record for release `v1.0.0`; or
- a guarantee that a sanitised review snapshot is unlinkable from older
  public versions of related work.

## Historical Reproducibility and Submission Gates

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

The review-stage frozen-state checks confirm that tests pass, both manifests
verify,
the manuscript has no unresolved citations/references, the Array validator
passes, and the flat package compiles in isolation.

## Production Follow-Up

- Wait for the publisher's production instructions before delivering files.
- Confirm author identity, affiliation, correspondence, ORCID, CRediT,
  funding and all required declarations in the requested production materials.
- Preserve the accepted scientific content and the original timing data;
  validate the supplied manifests without overwriting them with a new run.
- Review publisher proofs and any publishing agreement when supplied.
- Add publication metadata only when the publisher supplies it. An optional
  future archival deposit must use a real, assigned identifier.

The completed Array review tools, cover letter and checklist are retained as
historical records. They do not indicate that another resubmission is pending.

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
- 2026-09-23: distinguished that historical release from the substantially
  revised manuscript and regenerated evidence for the current resubmission;
  subsequently prepared a pinned, sanitised review snapshot.
- 2026-10-06: recorded the author's report of acceptance in Array, identified
  the exact research snapshot, and separated completed review-stage guidance
  from the pending publisher production workflow. Research results were not
  regenerated for this documentation update.
