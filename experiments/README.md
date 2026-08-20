# Reproducible evaluation

`run_all.py` executes the four evaluation groups and derives every reported
number from the checker and framework outputs:

- **E1 conformance:** all 19 committed handcrafted traces (5 positive and 14
  negative controls).
- **E2 framework validation:** one execution of each of the three deterministic
  LangGraph `StateGraph` workflows. One run is sufficient because these local
  workflows contain neither sampling nor external services.
- **E3 mutation testing:** 14 independently generated violation categories for
  each E2 canonical trace (42 cases). Strict detection means that the checker
  rejects the trace with exactly the expected code at the mutated step.
- **E4 scaling:** valid communication-only traces of 10, 100, 1,000, 5,000, and
  10,000 events, alternating messages and handoffs, with one warmup and seven
  measured repetitions by default. Timing includes rule indexing and excludes
  preparation of deep-copied inputs; it is not a benchmark of every event mix.

No cloud credentials, model API, or network access is required. The LangGraph
workflows use deterministic local tool functions. Native framework task IDs and
runtime measurements may vary between executions; acceptance counts, canonical
events, mutation labels, and generated table structure are deterministic.

## Run

From the repository root, using Python 3.12 and the pinned environment:

```sh
.venv/bin/python -m experiments.run_all
.venv/bin/python -m experiments.run_all --verify
```

The first command writes machine-readable JSON and CSV files to
`experiments/results/`, four LaTeX tables to `paper/generated/`, and a complete
SHA-256 inventory to `experiments/results/MANIFEST.json`. The second command
checks the expected inventory, file sizes, and hashes for both source inputs and
generated artifacts.

Individual groups are useful while developing:

```sh
.venv/bin/python -m experiments.run_all --only conformance
.venv/bin/python -m experiments.run_all --only framework
.venv/bin/python -m experiments.run_all --only mutations
.venv/bin/python -m experiments.run_all --only benchmark
```

A partial run writes only its own result files and table. It removes any stale
full-evaluation manifest; run the default `all` selection afterward to restore a
complete, verifiable artifact set. Benchmark parameters may be overridden with
`--lengths`, `--repetitions`, and `--warmups`.

## Test

```sh
.venv/bin/python -m unittest discover -s experiments/tests -v
```

The tests cover mutation labels, valid trace generation, framework execution,
the 42 framework-derived mutations, full artifact generation, manifest
verification, tamper detection, and partial-run invalidation.
