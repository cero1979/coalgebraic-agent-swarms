# Array Revision Notes

This file records the audit, scientific decisions, implementation changes, and
quality gates for the Regular Paper revision intended for *Array*. It is an
internal project log rather than a submission file.

## Revision branch

- Working branch: `array-resubmission-2026-08`
- Local base: `e66bda53fb281cfa2a684057b77b1095eb74d311`
- Source preserved: the locally modified `main.tex` dated 2026-07-06
- Previous reproducible tag: `jlamp-resubmission-2026-06`

The branch was deliberately created from the local base. The server-side
`main` branch had advanced to `c0a56053d213` through two deletion commits that
removed `COVER_LETTER.md` and `main.tex` while leaving the README, Makefile, and
manifest dependent on the missing manuscript. Pulling that state before
preserving the local source would have risked losing the latest editable
manuscript.

## Initial audit (2026-08-14)

### Repository and reproducibility

- The editable local manuscript is the most recent recoverable source. The
  local PDF has 36 pages.
- The existing deterministic conformance suite was rerun independently under
  Python 3.8.3 and Python 3.12: 19 traces, 5 accepted, 14 rejected.
- The two pre-existing unit tests pass under both interpreters.
- The generated conformance files are reproducible, but the committed manifest
  is stale because later manuscript changes were not followed by regeneration.
- No real LangGraph adapter, framework execution, systematic mutation study,
  runtime study, CI workflow, dependency lock, licence, or citation metadata
  existed at audit time.
- The file named `valid_langgraph_like_trace.json` is a hand-written canonical
  trace with framework-style metadata, not the output of a LangGraph run.

### Formal audit

The audit identified claims that cannot be retained in their current form:

- focused adequacy and bipolarity use an encoding that omits obligations and
  static policy facts required by the clauses;
- the cut corollary confuses admissible cut with forbidden contraction of
  linear resources;
- handoff and message rules leave the successor memory unconstrained even
  though local-soundness proofs assume it is unchanged;
- the shared-interface composition theorem lacks a fully defined combined
  coalgebra and conflicts with the stated subexponential accessibility order;
- the checker/calculus biconditional does not match multi-write events and the
  actual Python checks;
- the Python implementation copies growing state at every step, so its claimed
  worst-case linear bound does not follow;
- graph-induced SELL accessibility is described structurally but is not used by
  an implemented inference/checker rule.

Conservative decision: retain and repair the sound core (deterministic
coalgebraic behaviour, certified ledger transitions, conditional resource
preservation, prefix-closed safety, and executable conformance checking).
Remove or weaken unsupported results rather than presenting them as novelty.
Any complexity claim retained after refactoring must apply to the code that is
actually measured and tested.

### Current official Array requirements

Checked against the official *Array* Guide for Authors and current Elsevier
policies on 2026-08-14.

- Article type: Regular Paper. Only Technical Notes have the stated 10-page
  maximum; no explicit Regular Paper page limit was found.
- Abstract: at most 250 words.
- Keywords: 1--7.
- Highlights: encouraged, 3--5 bullets, at most 85 characters per bullet, in a
  separate editable file.
- Graphical abstract: encouraged rather than mandatory.
- References: numbered in order of appearance; data and software should be
  cited as research objects when applicable.
- Editable LaTeX sources, tables, equations, and separate figure files are
  required. The Editorial Manager LaTeX upload must be a flat bundle without
  subdirectories.
- Funding, competing interests, CRediT, data/software availability, and an
  accurate generative-AI declaration must be present.
- The current Elsevier CAS single-column class is an officially supported
  generic template and can be retained; no Array-specific class was found.

Author-side actions that cannot be completed automatically include the
Elsevier declaration-of-interest form, Editorial Manager metadata/contact
fields, APC/institutional-agreement review, and creation of an immutable DOI
release if the author chooses to archive the final repository in Zenodo.

## Response to the earlier JLAMP criticism

### Application appeared toy-like

Planned evidence:

- three deterministic workflows executed by the pinned LangGraph package;
- capture of framework-native stream/state updates;
- an explicit adapter from native records to canonical certification events;
- framework-valid trace checks and systematic seeded policy violations.

This will address the lack of external execution evidence, but it will not be
described as production-scale validation.

### Combination looked like an application of existing machinery

Revision decision:

- do not claim a universal new theory combining coalgebra and SELL;
- state the contribution as an executable resource-certification architecture;
- distinguish standard coalgebraic constructions from paper-specific ledger
  and certification results;
- retain only formal statements whose hypotheses and proofs survive audit.

### Real-world utility was unclear

Planned evidence:

- map exposed LangGraph routing, node updates, tool results, and run IDs to the
  canonical schema;
- state which policy facts are instrumentation rather than framework telemetry;
- report valid-trace acceptance, mutation rejection by obligation, and runtime
  measurements generated from committed machine-readable outputs.

The revision will not claim protection from adaptive attacks, factual truth of
tool output, protocol fidelity, liveness, or production scalability.

## Living change log

- 2026-08-14: completed the read-only Git, manuscript, formal, software, and
  journal-requirements audit.
- 2026-08-14: created `array-resubmission-2026-08` from the preserved local
  manuscript state.

## Quality gates

- [ ] Formal claims re-audited after edits
- [ ] Checker and adapter tests pass
- [ ] Real deterministic LangGraph workflows execute
- [ ] Conformance, framework, mutation, and runtime outputs regenerate
- [ ] Generated tables match machine-readable results
- [ ] Manifest verifies
- [ ] Manuscript compiles without undefined references
- [ ] PDF visually inspected
- [ ] Array submission validator passes
- [ ] Flat submission bundle compiles independently
- [ ] Clean-checkout reproduction tested where feasible
