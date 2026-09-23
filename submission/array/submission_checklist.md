# Array pre-submission status checklist

Status snapshot: 2026-09-23, after the reviewer-response revision, complete
automated build, and isolated package validation. `PASS` records objective
evidence already present. Historical release checks are identified as such.
It does not replace the author's scientific or publishing approval.

## Author and article metadata

- **PASS** - The public source, separate title page, and cover letter identify
  the work as a **Regular Paper** for **Array** and use the same article title;
  the generated review manuscript intentionally withholds author identifiers.
- **PASS** - The current abstract has 223 words, within the 250-word limit.
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

- **PASS** - `make all` compiled the revised manuscript to a 35-page PDF with no
  undefined citation or cross-reference in the final log.
- **PASS** - The submission validator found no missing, duplicate, or unused
  citation keys and BibTeX completed without warnings or errors.
- **PASS** - The frozen flat package contains both editable figure sources and
  every figure label is cited in the manuscript.
- **PASS** - The frozen flat package contains every editable/generated table
  source and every table label is cited in the manuscript.
- **PASS** - The builder creates a flat anonymous manuscript source archive,
  keeps the identified title page and cover letter as separate portal items,
  and records SHA-256 values for every generated upload file.
- **PASS** - Public tag `v1.0.0` remains an immutable identified research
  snapshot. The anonymous Editorial Manager packaging is generated locally from
  the same scientific sources and is intentionally not represented as part of
  that already-published immutable release.
- **PASS** - `make all` passed 57 tests: 26 checker, five LangGraph integration,
  fourteen experiment, and twelve submission-script tests; it also completed
  all builds and the isolated submission check.
- **HISTORICAL** - The August 20 E1--E4 release-candidate reproduction was
  recorded from clean commit `f4653a379471905cae2697eb35eb99f1d8eb3507`.
  The September 23 reviewer revision regenerated E1--E4 in the current working
  tree; its environment record correctly reports `repository_worktree_dirty:
  true`. The deterministic E1--E3 counts remain unchanged; E4 timings are new
  local measurements.
- **PASS** - Both result manifests verify all recorded SHA-256 entries, and the
  submission validator verifies every flat-bundle entry against
  `BUILD_MANIFEST.json`.
- **PASS** - The Array-specific `cover_letter.tex` exists, names the article
  type and destination, reports the evidence and limitations, and contains no
  stale journal correspondence.
- **PASS** - `title_page.docx` separately records name, affiliation, address,
  corresponding-author status, email, ORCID, CRediT roles, funding, and
  competing interests in the editable Word format requested by the portal;
  `title_page.tex` remains an editable LaTeX alternative.
- **PASS** - The anonymous manuscript source and bibliography contain no author
  name, email, ORCID, affiliation, repository username, or public self-release
  URL; they cite the separately uploaded anonymous supplement instead. The PDF
  uses the CAS `doubleblind` option and an empty author metadata field.
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
- **HISTORICAL** - Immutable public GitHub release `v1.0.0` identifies the
  earlier baseline and carries a signed release attestation. It does not
  contain this revision's regenerated E4 timings or revised manuscript. No
  archival DOI is claimed.
- **PASS** - The identified manuscript and bibliography cite the historical
  release accurately; the anonymous manuscript cites the version-matched
  supplementary archive instead. `CITATION.cff` describes release `v1.0.0`.
- **PASS** - A clean public release-candidate checkout passed committed-manifest
  verification and the complete documented pipeline without a private file,
  local-only path, LLM key, commercial API, or external research dataset.
- **PASS** - Repository visibility, release assets, SHA-256 inventory, software
  licence, data licence, and release attestation were verified after publication.
- **PASS** - The anonymous manuscript and cover letter currently rely on the
  locally generated, version-matched supplementary ZIP rather than an
  unavailable or identifying external mirror. Upload this ZIP as a separate
  supplementary item. The former `0CD6` mirror returned HTTP 401; the `D37C`
  mirror exposed author-identifying source content. Add a new URL only after
  signed-out accessibility, identity, and version checks all pass.
- **PASS** - The author explicitly authorised the remote update and publication
  of the final repository state and constructed artefacts.
- **MANUAL AUTHOR ACTION** - A future Zenodo deposit is recommended for FAIR
  discovery but is not an Array submission blocker. Add a DOI only after a real
  archival identifier has been assigned.

## Declarations and publishing conditions

- **PASS** - The manuscript contains a competing-interests statement.
- **MANUAL AUTHOR ACTION** - Reconfirm that there are no competing interests and
  update the manuscript and portal if circumstances have changed.
- **PASS** - The manuscript contains a funding statement saying that no specific
  grant supported the research.
- **MANUAL AUTHOR ACTION** - Reconfirm the funding statement and enter matching
  information in the portal.
- **PASS** - The identified CRediT statement is in the separate title page; the
  anonymous manuscript contains only a neutral pointer to that file.
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
- **PASS** - The revised 35-page anonymous manuscript compiled and representative
  opening, evaluation, and closing pages were visually inspected without
  clipping, overlap, broken tables, missing figures, unresolved references,
  placeholders, or missing glyphs. The ten-page response-to-reviewers PDF was
  also rendered and inspected. The August 20 full-page inspection applied to
  the preceding 34-page version, not automatically to this revision.
- **PASS** - The final PDFs were compiled from the frozen editable sources and
  checked against them for title, author, abstract, keywords, figures, tables,
  declarations, references, and cover-letter statements.
- **MANUAL AUTHOR ACTION** - Upload every required LaTeX dependency using the
  classifications in `README_SUBMISSION.md`; upload administrative Markdown and
  the integrity manifest only if requested.
- **MANUAL AUTHOR ACTION** - Complete all remaining Editorial Manager questions
  and publisher declarations; do not treat local validation as completion of a
  publisher form.
- **BLOCKED** - Preview and compare the portal-generated submission PDF with the
  locally validated `main.pdf` before approving the submission.
