# Cover letter - resubmission to JLAMP

**To:** Alberto Lluch Lafuente, Editor-in-Chief

**Journal of Logical and Algebraic Methods in Programming**

**Re:** Resubmission of "A Coalgebraic and Resource-Sensitive Semantics for
Tool-Augmented Agent Swarms" (C. Ramirez Ovalle)

Dear Professor Lluch Lafuente,

Thank you for the opportunity to resubmit a substantially revised version of
this manuscript. We are grateful for the handling editor's precise assessment.
The principal concern was that the paper did not establish its novelty against
the mature literature on composite communicating systems, especially process
algebra, mobile calculi, and session types. The revision addresses that concern
directly and also corrects several statements whose earlier formulation was
broader than their proofs supported.

The revised manuscript now presents the contribution as a deliberately limited
structural coupling between two layers: a coalgebra indexed by an interaction
graph describes possible behaviour, while a side-conditioned SELL program uses
the same graph to constrain resource-zone accessibility and to recognise
certified executions. We do not claim a bialgebraic distributive law, full SELL
proof search, protocol fidelity, deadlock-freedom, or probabilistic results.

## Response to the main concern: novelty and comparison

> "In order to show the results' novelty and scientific value, the comparison
> with other works that tackles the same problem (or similar ones) is a must."

We agree. The Related Work section now includes a dedicated subsection and a
technical comparison table covering CCS, CSP, the pi-calculus, propositions as
sessions, resource-aware session types, and bialgebraic semantics.

The revised comparison makes the boundaries explicit:

- CCS, CSP, and the pi-calculus already provide the classical notions of
  communication, mobility, traces, and bisimulation used by the paper. We do not
  claim novelty for interaction graphs, message/handoff events, or behavioural
  equivalence.
- Session types govern the shape of a channel protocol and, under the relevant
  type-system assumptions, establish protocol fidelity and progress properties.
  Our calculus does not type dual endpoints and does not establish those
  properties.
- Resource-aware session types integrate cost or potential with the channel
  protocol. Our framework instead keeps permissions, budgets, provenance,
  certified claims, and audit evidence in a ledger separate from the behavioural
  functor.
- Bialgebraic semantics couples syntax and behaviour through a distributive law.
  The present paper does not provide such a law; it filters an already-given raw
  coalgebra by side-conditioned certificate rules.

The distinguishing contribution is therefore not a replacement for those
formalisms. It is the raw/certified separation for resource-governed executions,
with quantitative budget accounting, append-only provenance, audit freshness,
and answer support in one executable certificate discipline.

## Issue 1: limited interplay between coalgebra and SELL

> "The use of the two techniques is mostly separate. Little nontrivial interplay
> between the two."

The revision now states the coupling precisely and no longer overstates it.

1. The interaction graph indexing the swarm coalgebra generates the
   agent-to-agent part of the subexponential preorder.
2. The graph-characterisation proposition now proves that the quotient of the
   agent-label preorder is isomorphic to the reachability order of the graph's
   strongly connected components. Thus the signature retains exactly the
   condensation order, rather than merely repeating a list of edges.
3. Direct graph edges constrain message and handoff events, while reachability
   constrains which agent zones a focused certificate rule may inspect.
4. The composition theorem has been reformulated with the necessary
   non-interference hypotheses: disjoint agents, tagged memory/claim/audit
   namespaces, product state, and no cross-component reads. Under those
   hypotheses, local certificates lift to interleaved composition. Shared-memory
   or interface composition is now explicitly identified as requiring combined
   verification.

This is a structural graph-to-signature coupling, not a distributive law between
SELL syntax and coalgebraic behaviour. The manuscript states that limitation in
the Introduction, Related Work, Discussion, and Limitations sections.

## Issue 2: abstraction power of coalgebra

> "The abstraction power of the theory of coalgebra is not exploited (it is
> applied only to Moore and Mealy machines)."

The revision distinguishes generic facts from the deterministic instantiation.
Final behaviour and bisimulation invariance depend only on the chosen functor
and final coalgebra; the subcoalgebra construction is the standard factorisation
pattern for a functor preserving the relevant inclusion. The event and ledger
rules are instantiated to the deterministic Mealy functor because they inspect
concrete finite steps.

We also corrected the certified-bisimulation theorem. Certified bisimulation is
now explicitly a two-way relation on the closed certifiable subcoalgebra
`X_cert`. Only on that domain does it imply equality of raw observable
behaviour. The partial certified LTS outside `X_cert` is used for safety
monitoring but is not claimed to determine raw behavioural equivalence.

The distribution-functor construction is retained only as an extension point.
No probabilistic theorem is claimed.

## Minor comment 1: standard Propositions 1 and 2

> "Results such as Prop. 1 and 2 are very standard and do not have to be proved.
> A reference is enough."

Done. The final Moore and deterministic Mealy constructions are cited as
standard results. Only their characteristic equations, which are used later,
are retained.

## Minor comment 2: SELL signature and contexts

> "For Def. 6, the definition of subexponential signature is desired in the
> paper (not only in a reference). So is that of linear and subexponential
> context."

Done. The Preliminaries now defines `Sigma = (I, <=, U)`, including the
upward-closure requirement on `U`, and defines the linear context `Delta` and
labelled context `Theta` before the certified-transition judgement. The concrete
signature includes a reusable program zone, reusable policy and permission
zones, and linear budget and audit-obligation resources.

## Additional correctness and reproducibility revisions

During the final audit we made the following further corrections.

1. The six displayed rules are now described as a side-conditioned operational
   certificate calculus. Their resource transformations are reusable SELL
   program clauses; arithmetic, graph membership, payload policy, and freshness
   remain explicit external evidence. The checker correspondence is not
   presented as completeness for pure SELL.
2. The complexity statement now gives the actual bound: expected `O(s + N)` for
   specification size `s` and trace representation size `N`, or expected `O(N)`
   for a fixed specification. The previous, incorrect MELL/SELL complexity
   contrast has been removed. The manuscript notes correctly that MALL is
   PSPACE-complete and full propositional linear logic is undecidable, while
   making no reduction or speed-up claim.
3. Budget preservation now uses an explicit sufficiency inequality before
   subtraction, avoiding truncated subtraction in the natural numbers.
4. The conformance suite now contains 19 traces: 5 accepted scenarios and 14
   rejected controls, including a payload-policy violation. The checker output
   is deterministic across supported Python versions, and a manifest verifier
   checks every recorded SHA-256 value.
5. The public repository now includes the manuscript source and required LaTeX
   class files, so `make all` works from a clean checkout. Documentation no
   longer calls a mutable branch an archive.
6. Submission highlights are provided as a separate editable file, each within
   Elsevier's 85-character limit, and the required generative-AI preparation
   declaration is included before the references.

We believe the revision now answers the editor's comparison request directly,
states the coalgebra-SELL interaction at the strength actually proved, and makes
the formal and executable claims independently auditable.

Sincerely,

Carlos Ramirez Ovalle

Pontificia Universidad Javeriana-Cali

carlosovalle@javerianacali.edu.co
