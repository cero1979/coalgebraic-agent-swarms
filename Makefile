PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
LATEXMK ?= latexmk
EXPERIMENT_RUNNER := $(PYTHON) -m experiments.run_all
SUBMISSION_DIR ?= submission/array

.DEFAULT_GOAL := help
.NOTPARALLEL:

.PHONY: help test results prototype-results conformance framework mutations \
	benchmark experiments verify paper submission submission-check all clean

help: ## List the reproducibility targets.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run checker, integration, experiment, and submission-script unit tests.
	$(PYTHON) -m unittest discover -s prototype -p 'test*.py'
	$(PYTHON) -m unittest discover -s integrations/langgraph/tests -p 'test*.py'
	$(PYTHON) -m unittest discover -s experiments/tests -p 'test*.py'
	$(PYTHON) -m unittest discover -s scripts/tests -p 'test*.py'

prototype-results: ## Regenerate the original 19-trace checker artifacts.
	$(PYTHON) prototype/checker.py \
		--rules prototype/rules.json \
		--traces prototype/traces/*.json \
		--out-dir prototype/results

results: prototype-results ## Backward-compatible alias for prototype-results.

conformance: ## Run E1, the fixed positive/negative conformance suite.
	$(EXPERIMENT_RUNNER) --only conformance

framework: ## Run E2, deterministic executions of the real LangGraph workflows.
	$(EXPERIMENT_RUNNER) --only framework

mutations: ## Run E3, controlled mutations of framework-generated traces.
	$(EXPERIMENT_RUNNER) --only mutations

benchmark: ## Run E4, the checker scaling benchmark.
	$(EXPERIMENT_RUNNER) --only benchmark

experiments: ## Regenerate E1-E4 results, paper tables, and their manifest.
	$(EXPERIMENT_RUNNER)

verify: ## Verify the legacy and E1-E4 SHA-256 manifests.
	$(PYTHON) prototype/verify_manifest.py prototype/results/MANIFEST.json
	$(EXPERIMENT_RUNNER) --verify

paper: ## Compile main.pdf from the editable manuscript source.
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error main.tex

submission: experiments paper ## Regenerate evidence and build the flat, independently compilable Array package.
	$(PYTHON) scripts/build_submission.py --output $(SUBMISSION_DIR)

submission-check: submission ## Validate objective Array constraints and isolated compilation.
	$(PYTHON) scripts/validate_submission.py --bundle $(SUBMISSION_DIR)

all: test experiments prototype-results verify paper submission-check ## Run the deterministic end-to-end pipeline.

clean: ## Remove local build caches and LaTeX auxiliary files; retain results and PDFs.
	-$(LATEXMK) -c main.tex
	@if [ -d "$(SUBMISSION_DIR)" ]; then \
		$(LATEXMK) -c -cd "$(SUBMISSION_DIR)/main.tex" 2>/dev/null || true; \
		$(LATEXMK) -c -cd "$(SUBMISSION_DIR)/cover_letter.tex" 2>/dev/null || true; \
	fi
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
