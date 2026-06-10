# Cover letter — resubmission to JLAMP

**To:** Alberto Lluch Lafuente, Editor-in-Chief
**Journal of Logical and Algebraic Methods in Programming**

**Re:** Resubmission of manuscript **[PREVIOUS REFERENCE NUMBER]**,
"A Coalgebraic and Resource-Sensitive Semantics for Tool-Augmented Agent Swarms"
(C. Ramírez Ovalle)

Dear Professor Lluch Lafuente,

Thank you for the opportunity to resubmit a substantially revised version of the
above manuscript, previously handled under reference **[PREVIOUS REFERENCE NUMBER]**.
We are grateful to the handling editor for a constructive and precise review. The
central recommendation—that the paper must be positioned against existing work on
the behaviour of composite communicating systems, especially process algebra,
mobile calculi, and session types—was well taken, and addressing it has clarified
what is genuinely new in the contribution. Below we respond point by point and
summarise the corresponding changes. All new text is in the Related Work,
Preliminaries, Introduction, and Discussion sections; no formal result was
weakened, and the artefact is unchanged.

---

## Response to the handling editor's main concern (novelty and comparison)

> *"In order to show the results' novelty and scientific value, the comparison
> with other works that tackles the same problem (or similar ones) is a must."*

We agree. The revised paper now contains a dedicated comparison and a sharper
statement of what the combination of coalgebra and SELL delivers that prior
formalisms do not. Crucially, we also followed the editor's hint that the
real potential of the work lies in its use of SELL, and we have foregrounded
the one result that genuinely couples the two techniques (the graph-determined
subexponential preorder) together with its computational consequence (linear-time
certificate checking versus PSPACE/EXPTIME proof search). See the responses to
Issues 1–3 below.

---

## Issue 3 — Comparison with process algebra, mobile calculi, and session types

> *"Reasoning about the behavior of composite systems is an old problem... Comparison
> with those works is a must."*

This was the decisive comment, and we have addressed it directly.

**New Related Work subsection "Process algebra, mobile calculi, and session
types."** It (i) acknowledges CCS, CSP, and the π-calculus as the mature prior
art that supplies our conceptual vocabulary (communication, delegation,
behavioural equivalence), and explicitly states that our interaction graph,
message/handoff events, and swarm bisimulation are classical rather than novel in
this respect; (ii) discusses the propositions-as-sessions correspondence
(Caires–Pfenning, Wadler, Honda et al., Hüttel et al.) as the closest body of
work linking linear logic to concurrency; and (iii) draws the distinguishing
line precisely.

**Our answer to the editor's two-way question is the second option: the problem
is related, but the method has distinguishing features.** Concretely:

- Session-type systems use a linear proposition to type a *channel and its dual*,
  so the discipline guarantees *protocol fidelity and deadlock-freedom* between
  endpoints; the resource under control is the interaction protocol.
- Our framework does not type channels, require duality, or target
  deadlock-freedom. Messages and handoffs are constrained only by *graph
  admissibility*, which is strictly weaker than session fidelity. Instead, the
  *subexponential* layer stratifies resources into labelled zones with different
  structural status (reusable tool permissions and trace evidence vs. consumable
  budgets and audit obligations), and certification binds these to *quantitative
  budget accounting, append-only provenance memory, and answer support*—exactly
  the aspects a session type abstracts away.

We also compare against the closest quantitative relative, **resource-aware
session types** (Das–Hoffmann–Pfenning), explaining that they fold cost into the
behavioural type of a channel, whereas we keep the budget/permission/provenance/
audit ledger as a *separate component of the coalgebraic state*, decoupled from
the behavioural functor and from channel duality. This decoupling is what makes
the raw/certified separation and the prefix-closed safety sublanguage possible.
Finally, we relate the work to **bialgebraic semantics** (Turi–Plotkin), stating
honestly that we do *not* give a distributive-law/GSOS specification and
identifying that coupling as future work.

New references added: Milner (CCS), Hoare (CSP), Milner–Parrow–Walker
(π-calculus), Caires–Pfenning, Wadler, Honda–Vasconcelos–Kubo, Hüttel et al.,
Das–Hoffmann–Pfenning, and Turi–Plotkin.

---

## Issue 1 — Limited interplay between the two techniques

> *"The use of the two techniques is mostly separate. Little nontrivial interplay
> between the two."*

We have foregrounded the result that *is* the interplay. The introduction now
states explicitly that the SELL signature is **not chosen independently of the
dynamics**: Proposition (graph-dependent structure of the signature) shows that
the subexponential preorder is *uniquely determined by the reachability structure
of the interaction graph that indexes the coalgebra*. In other words, the logical
layer is read off the behavioural layer rather than layered on top of it. This
links directly to the compositionality theorem, whose proof uses exactly this
graph-to-preorder determination to show that disjoint swarms compose without
global re-verification.

---

## Issue 2 — Abstraction power of coalgebra not fully exploited

> *"The abstraction power of the theory of coalgebra is not exploited (it is
> applied only to Moore and Mealy machines)."*

As the editor noted, once Issue 3 is resolved this point can be treated lightly,
and we have done so while still improving the presentation. We have (i) made the
certified-subcoalgebra construction explicit as a genuine coalgebraic
substructure embedded by a morphism into the raw coalgebra, with observable
behaviour compared through the final coalgebra, and (ii) kept the probabilistic
(distribution-functor) variant explicit as the natural generalisation beyond the
deterministic Mealy presentation. We deliberately retain the deterministic core
because the resource-preservation theorem concerns certified finite executions;
this scope is now stated as an explicit assumption rather than an implicit choice.

---

## Minor comment 1 — Propositions 1 and 2 are standard

> *"Results such as Prop. 1 and 2 are very standard and do not have to be proved.
> A reference is enough."*

Done. The full finality proofs of Proposition 1 (final Moore semantics) and
Proposition 2 (final semantics for deterministic swarms) have been replaced by
references to the standard theory of coalgebras and Moore/Mealy automata
(Rutten; Jacobs; Bonsangue–Rutten–Silva for Mealy machines). We retained only the
characteristic equations of the behaviour map, since these—rather than the
finality construction—are what later proofs actually use.

---

## Minor comment 2 — Definition of subexponential signature and contexts

> *"For Def. 6, the definition of subexponential signature is desired in the paper
> (not only in a reference). So is that of linear and subexponential context."*

Done. A new Preliminaries subsection "Subexponential linear logic" now gives, in
the paper itself and **before** the certified-transition definition (Def. 6),
explicit definitions of the subexponential signature `Σ = (I, ⪯, U)` and of the
linear context `Δ` and subexponential context `Θ`. Definition 6 now references
these definitions directly, and the later "Subexponential signature" subsection
recalls them before instantiating the signature for a swarm.

---

## Summary of changes

1. New Related Work subsection comparing with process algebra, mobile calculi,
   and session types (Issue 3), with nine new references.
2. New Preliminaries subsection defining the SELL signature and the linear and
   subexponential contexts, referenced from Definition 6 (Minor comment 2).
3. Proofs of Propositions 1 and 2 replaced by references plus the characteristic
   equations actually used downstream (Minor comment 1).
4. Introduction strengthened to foreground the graph-determined preorder as the
   genuine coalgebra–SELL interplay (Issue 1) and the linear-time vs. PSPACE/
   EXPTIME complexity contrast as the concrete technical result.
5. Discussion extended to contrast SELL-based certification with session types
   for communicating endpoints (Issue 3).

We believe these revisions resolve the comparison concern that motivated the
decision and make the specific novelty—the coupling of coalgebraic dynamics with
a graph-determined, linearly-checkable subexponential certification discipline—
explicit. We thank the editor again for guidance that materially improved the
paper.

Sincerely,

Carlos Ramírez Ovalle
Pontificia Universidad Javeriana-Cali
carlosovalle@javerianacali.edu.co
