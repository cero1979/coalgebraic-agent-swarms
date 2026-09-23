ANONYMOUS REPLICATION PACKAGE

This archive contains the checker, 19 conformance traces, three deterministic
LangGraph workflows, E1-E4 experiment code and outputs, generated tables, and
integrity manifests. It uses no LLM, API key, or commercial service.

Setup:
  python3.12 -m venv .venv
  . .venv/bin/activate
  python -m pip install -r requirements.txt

Checks:
  python -m unittest discover -s prototype -p 'test*.py'
  python -m unittest discover -s integrations/langgraph/tests -p 'test*.py'
  python -m unittest discover -s experiments/tests -p 'test*.py'
  python prototype/verify_manifest.py prototype/results/MANIFEST.json
  python -m experiments.run_all --verify
