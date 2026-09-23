# Deterministic LangGraph integration

This package executes three real `StateGraph` workflows with LangGraph 1.2.11,
captures the framework's native v2 `tasks`, `updates`, and `values` streams, and
normalizes application emissions from those streams into the event list accepted
by `prototype.checker.check_trace`. It does not construct a canonical trace in
place of framework execution: canonical events are produced only from updates
observed while the compiled graph is running.

The validation is deterministic and local. It uses ordinary Python node behavior
and deterministic tool functions, with no language model, network call, API key,
or paid service.

## Reproduce

Python 3.12 and the exact dependency pin are required:

```bash
/usr/local/bin/python3.12 -m venv .venv-langgraph
.venv-langgraph/bin/python -m pip install -r integrations/langgraph/requirements.txt
.venv-langgraph/bin/python -m unittest discover -s integrations/langgraph/tests -v
.venv-langgraph/bin/python -m integrations.langgraph.run_workflows \
  --workflow all --run-id deterministic-demo
```

The public Python API is:

```python
from integrations.langgraph import run_workflow

run = run_workflow("research", "paper-run-001")
native_records = run["native_stream"]
canonical_events = run["canonical_trace"]
```

`run_workflow(name, run_id)` accepts `research`, `resource_controlled`, or
`shared_memory`. Its result is JSON-serializable and includes the final LangGraph
state as well as both trace representations.

## Workflows

| Workflow | Actual graph behavior | Canonical obligations exercised |
|---|---|---|
| `research` | Planner routes to Retriever; Retriever executes a deterministic bibliographic search; Verifier checks and certifies; Planner answers | handoffs, message, two permitted tools, provenance write, certificate, supported answer |
| `resource_controlled` | A budget gate conditionally schedules a second search before verification | conditional routing, two cost-2 searches under budget 5, permission, budget ledger, audit events |
| `shared_memory` | Retriever writes a source; Verifier reads it and appends a derived record; Planner consumes the certified claim | cross-component read, append-only writes, explicit derivation provenance, certification, answer support |

## Normalization boundary

LangGraph supplies graph scheduling, node updates, task identifiers, and the
stream envelope. Domain meanings such as "this node is the Retriever" or "this
write is a source" are explicit instrumentation returned by the deterministic
node; LangGraph does not infer them.

| Native LangGraph/instrumented value | Canonical value | Treatment |
|---|---|---|
| v2 task `name` | `framework.node` | preserved |
| v2 task `id` | `framework.task_id` | preserved as framework metadata |
| execution `run_id` | `framework.run_id`; audit-id prefix | preserved, then used to infer a unique audit identifier |
| update emission `route` | `handoff` | normalized from explicit actor and recipient fields |
| update emission `message` | `message` | normalized |
| update emission `tool_invocation` | `tool_call` | normalized; operation and supplied inputs are preserved |
| update emission `state_write` | `shared_memory_update` | normalized |
| native write `namespace/address/content` | write `scope/key/value` | normalized without changing the value |
| native write `provenance` | write `provenance` | preserved and augmented with the canonical audit trace |
| update emission `claim_certificate` | `certify` | normalized |
| update emission `final_output` | `answer` | normalized |
| stream position | canonical `step` | inferred monotonically from observed emissions |
| state-only updates and cumulative `values` | no canonical event | retained in `native_stream`, intentionally not mapped |

The adapter discards no captured native records: the complete JSON-safe stream is
returned alongside the canonical trace. It does omit state-only scheduling details
from the canonical event list because the checker has no corresponding event kind.

LangGraph does not expose or establish tool permissions, SELL costs, factual truth,
claim validity, hidden model reasoning, or the provenance of uninstrumented external
effects. The checker obtains permissions and costs from `prototype/rules.json`.
Provenance here establishes a structural derivation path from an observed,
instrumented write; it is not a guarantee that a source is factually correct.
