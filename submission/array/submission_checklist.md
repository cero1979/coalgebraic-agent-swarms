# Array pre-submission status checklist

Status snapshot: 2026-08-20, after the complete automated build and before the
final clean-result capture and visual inspection. `PASS` records objective
evidence already present. It does not replace the author's scientific or
publishing approval.

## Author and article metadata

- **PASS** - The current source and cover letter identify the work as a
  **Regular Paper** for **Array** and use the same article title.
- **PASS** - The current abstract has 217 words, within the 250-word limit.
- **PASS** - The current manuscript has seven keywords, within the 1--7 limit.
- **PASS** - `HIGHLIGHTS.md` has five highlights; their lengths are 67, 70, 70,
  72, and 73 characters, all within the 85-character limit.
- **MANUAL AUTHOR ACTION** - Verify the author's spelling, affiliation,
  department, street address, city, country, corresponding-author status,
  email, and ORCID against authoritative records. Do not infer or add a
  telephone number or postal code.
- **MANUAL AUTHOR ACTION** - Confirm that the CRediT roles accurately describe
  the sole author's work.
- **MANUAL AUTHOR ACTION** - Enter and recheck the article type, title, abstract,
  keywords, author details, funding, and classifications in Editorial Manager.

## Scientific verification

- **MANUAL AUTHOR ACTION** - Independently re-read every theorem, proposition,
  proof, definition, and scope statement; confirm that each claim is supported
  at exactly the strength stated.
- **MANUAL AUTHOR ACTION** - Independently verify every bibliography record
  against its primary source, including authors, title, venue, year, pages,
  URL, and DOI where one genuinely exists.
- **MANUAL AUTHOR ACTION** - Confirm that the recent comparison literature is
  characterised accurately and that the article does not imply empirical
  superiority over systems or benchmarks it did not compare experimentally.
- **PASS** - The current manuscript explicitly limits its evidence to finite
  deterministic executions, synthetic workflows, one external framework,
  structural provenance, and a side-conditioned certificate fragment.
- **MANUAL AUTHOR ACTION** - Confirm the final manuscript does not claim full
  SELL proof search, mechanisation, factual correctness, authenticated
  provenance, adversarial security, or production-scale generality.

## Final technical freeze

- **PASS** - `make all` compiled the final manuscript to a 34-page PDF with no
  undefined citation or cross-reference in the final log.
- **PASS** - The submission validator found no missing, duplicate, or unused
  citation keys and BibTeX completed without warnings or errors.
- **PASS** - The frozen flat package contains both editable figure sources and
  every figure label is cited in the manuscript.
- **PASS** - The frozen flat package contains every editable/generated table
  source and every table label is cited in the manuscript.
- **PASS** - The builder collected a 19-file flat submission package containing
  the manuscript source, bibliography, Elsevier class/style files, flattened
  figure/table sources, highlights, cover letter, PDFs, and integrity manifest.
- **BLOCKED** - The repository is currently modified and untracked files remain;
  do not describe the source snapshot as clean until the intended files are
  committed and `git status --short` is empty.
- **PASS** - `make all` passed 56 tests: 26 checker, five LangGraph integration,
  fourteen experiment, and eleven submission-script tests; it also completed
  all builds and the isolated submission check.
- **BLOCKED** - Final experiment reproduction is not yet recorded for the frozen
  source commit. Regenerate all results and tables after the source freeze.
- **PASS** - Both result manifests verify all recorded SHA-256 entries, and the
  submission validator verifies every flat-bundle entry against
  `BUILD_MANIFEST.json`.
- **PASS** - The Array-specific `cover_letter.tex` exists, names the article
  type and destination, reports the evidence and limitations, and contains no
  stale journal correspondence.
- **PASS** - The flat-bundle builder and objective submission validator are
  present in `scripts/`, and their intended commands are documented in
  `README_SUBMISSION.md`.

## Recorded experimental evidence

- **PASS** - The current generated E1 summary records 19 expectation matches:
  five accepted traces and fourteen rejected controls.
- **PASS** - The current generated E2 summary records three accepted executions
  from three deterministic LangGraph 1.2.11 workflows, with retained native
  version-2 records before canonicalisation.
- **PASS** - The current generated E3 summary records strict detection of all 42
  mutations: fourteen categories applied to each of three source traces, with
  rejection at the mutated step and the expected violation code.
- **PASS** - The current generated E4 summary covers 10, 100, 1,000, 5,000, and
  10,000 communication events with one warm-up and seven measured repetitions
  per size.
- **MANUAL AUTHOR ACTION** - Inspect the final environment metadata and confirm
  Python, dependency versions, hardware, architecture/translation status, and
  recorded source commit before quoting or archiving it.
- **MANUAL AUTHOR ACTION** - Preserve the interpretation boundary: E4 is a
  checker scaling sanity check, not an LLM or framework-performance benchmark.

## Data, software, and archive

- **PASS** - The current data-availability text identifies all reported inputs
  and outputs as original synthetic data generated for this study; the
  experiment design uses no external research dataset.
- **NOT APPLICABLE** - Human-subject, personal, clinical, animal, and
  third-party-dataset ethics/consent requirements do not apply to the documented
  synthetic deterministic evaluation.
- **MANUAL AUTHOR ACTION** - In the source-of-data form, select **Original
  data**, not Reference data.
- **MANUAL AUTHOR ACTION** - Enter the dataset title exactly as:
  **Coalgebraic Agent Swarms: Conformance Traces and LangGraph Validation
  Outputs**.
- **BLOCKED** - No immutable public software/data release and archival record
  with a persistent identifier has been created. Create both before submission;
  do not invent a DOI or call a mutable branch an archive.
- **BLOCKED** - Artifact and dataset references cannot be finalised until that
  release exists. Then update `main.tex`, `references.bib`, the data/software
  availability text, repository metadata, and portal fields to the same release
  and persistent identifier.
- **BLOCKED** - Public reproducibility cannot be signed off until the immutable
  release is opened from a clean checkout and its documented commands run
  without private files, local-only paths, an LLM key, or a commercial API.
- **BLOCKED** - Repository visibility, release assets, checksums, licensing, and
  long-term archive access require verification after publication of the
  immutable release.
- **PASS** - This local preparation has performed **no remote push**, public
  release, or archival deposit.
- **MANUAL AUTHOR ACTION** - Approve the exact release contents before any
  remote push, create the release/archive, and retain the resulting identifiers
  and checksums.

## Declarations and publishing conditions

- **PASS** - The manuscript contains a competing-interests statement.
- **MANUAL AUTHOR ACTION** - Reconfirm that there are no competing interests and
  update the manuscript and portal if circumstances have changed.
- **PASS** - The manuscript contains a funding statement saying that no specific
  grant supported the research.
- **MANUAL AUTHOR ACTION** - Reconfirm the funding statement and enter matching
  information in the portal.
- **PASS** - The manuscript contains a CRediT authorship contribution statement.
- **PASS** - The manuscript contains a generative-AI declaration that describes
  Codex assistance beyond grammar-only editing and assigns review and
  responsibility to the author.
- **MANUAL AUTHOR ACTION** - Review and explicitly approve the final
  generative-AI declaration against actual use and current publisher policy.
- **MANUAL AUTHOR ACTION** - Confirm originality, absence of simultaneous
  submission, sole-author approval, and authority to submit the software and
  data.
- **MANUAL AUTHOR ACTION** - Complete the publisher's official
  declaration-of-interest tool/document if required and ensure every answer
  matches the manuscript and Editorial Manager metadata.
- **MANUAL AUTHOR ACTION** - Confirm that no third-party figure, table, code, or
  text permission is required; add permission records if that assessment
  changes.
- **MANUAL AUTHOR ACTION** - Check the current open-access article publishing
  charge, taxes, currency, institutional agreement, waiver/discount eligibility,
  and funding responsibility before submission.

## Package and portal approval

- **PASS** - `make all` invoked `make submission-check`; the objective validator
  reported that the package is flat, complete, and independently compilable.
- **PASS** - `BUILD_MANIFEST.json` matches every recorded flat-bundle file; no
  nested directory or prohibited auxiliary file is present.
- **BLOCKED** - Visually inspect every page of final `main.pdf` and
  `cover_letter.pdf` for clipping, blank pages, broken tables, missing figures,
  unresolved references, and malformed hyperlinks.
- **BLOCKED** - Confirm the final PDFs match the frozen source in title, author,
  abstract, keywords, figures, tables, declarations, references, and
  cover-letter statements.
- **MANUAL AUTHOR ACTION** - Upload every required LaTeX dependency using the
  classifications in `README_SUBMISSION.md`; upload administrative Markdown and
  the integrity manifest only if requested.
- **MANUAL AUTHOR ACTION** - Complete all remaining Editorial Manager questions
  and publisher declarations; do not treat local validation as completion of a
  publisher form.
- **BLOCKED** - Preview and compare the portal-generated submission PDF with the
  locally validated `main.pdf` before approving the submission.
