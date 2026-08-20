"""Real deterministic LangGraph integration for the certification checker."""

from .adapter import AdapterError, normalize_stream
from .schema import PINNED_LANGGRAPH_VERSION, WorkflowName, WorkflowRun
from .workflows import available_workflows, build_workflow


def run_workflow(name: WorkflowName, run_id: str) -> WorkflowRun:
    """Lazily import the runner so ``python -m`` executes without warnings."""

    from .run_workflows import run_workflow as execute

    return execute(name, run_id)

__all__ = [
    "AdapterError",
    "PINNED_LANGGRAPH_VERSION",
    "available_workflows",
    "build_workflow",
    "normalize_stream",
    "run_workflow",
]
