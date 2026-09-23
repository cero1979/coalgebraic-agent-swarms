PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
LATEXMK ?= latexmk
EXPERIMENT_RUNNER := $(PYTHON) -m experiments.run_all

.DEFAULT_GOAL := help
.NOTPARALLEL:

.PHONY: help test prototype-results conformance framework mutations benchmark \
	experiments verify paper paper-tables check all reproduce clean

help: ## List the reproducibility targets.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run the 45 checker, integration, and experiment unit tests.
	$(PYTHON) -m unittest discover -s prototype -p 'test*.py'
	$(PYTHON) -m unittest discover -s integrations/langgraph/tests -p 'test*.py'
	$(PYTHON) -m unittest discover -s experiments/tests -p 'test*.py'

prototype-results: ## Regenerate the 19-trace checker artifacts.
	$(PYTHON) prototype/checker.py \
		--rules prototype/rules.json \
		--traces prototype/traces/*.json \
		--out-dir prototype/results

conformance: ## Run E1, the fixed conformance suite.
	$(EXPERIMENT_RUNNER) --only conformance

framework: ## Run E2, the three deterministic LangGraph workflows.
	$(EXPERIMENT_RUNNER) --only framework

mutations: ## Run E3, controlled mutations of framework-generated traces.
	$(EXPERIMENT_RUNNER) --only mutations

benchmark: ## Run E4, the checker scaling benchmark.
	$(EXPERIMENT_RUNNER) --only benchmark

experiments: ## Regenerate E1-E4 results, paper tables, and their manifest.
	$(EXPERIMENT_RUNNER)

verify: ## Verify the supplied checker and E1-E4 SHA-256 manifests.
	$(PYTHON) prototype/verify_manifest.py prototype/results/MANIFEST.json
	$(EXPERIMENT_RUNNER) --verify

paper-tables: ## Copy regenerated tables into the flat LaTeX source layout.
	cp paper/generated/conformance_table.tex paper__generated__conformance_table.tex
	cp paper/generated/framework_validation_table.tex paper__generated__framework_validation_table.tex
	cp paper/generated/mutation_table.tex paper__generated__mutation_table.tex
	cp paper/generated/runtime_table.tex paper__generated__runtime_table.tex

paper: ## Compile the anonymous manuscript from the current flat sources.
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error main.tex

check: test verify paper ## Check supplied evidence and compile the manuscript.

reproduce: test experiments prototype-results verify paper-tables paper ## Regenerate all evidence and compile the manuscript.

all: reproduce ## Run the full research pipeline described in the manuscript.

clean: ## Remove LaTeX auxiliary files; retain supplied results and PDFs.
	$(LATEXMK) -c main.tex
