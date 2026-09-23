"""Public execution API and CLI for deterministic LangGraph validation runs."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from .adapter import normalize_stream
from .schema import PINNED_LANGGRAPH_VERSION, WorkflowName, WorkflowRun
from .workflows import available_workflows, build_workflow


STREAM_MODES = ("tasks", "updates", "values")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump(mode="json"))
    raise TypeError(f"LangGraph stream contains non-serializable value {type(value)!r}")


def run_workflow(name: WorkflowName, run_id: str) -> WorkflowRun:
    """Execute one StateGraph and return native plus canonical traces."""

    installed_version = version("langgraph")
    if installed_version != PINNED_LANGGRAPH_VERSION:
        raise RuntimeError(
            f"expected langgraph=={PINNED_LANGGRAPH_VERSION}, found {installed_version}"
        )
    graph, initial_state = build_workflow(name, run_id)
    native_stream: list[dict[str, Any]] = []
    final_state: dict[str, Any] = {}
    deterministic_run_uuid = uuid5(NAMESPACE_URL, f"coalgebraic-agent-swarms:{name}:{run_id}")
    config = {
        "run_id": deterministic_run_uuid,
        "run_name": f"coalgebraic-agent-swarms-{name}",
        "tags": ["deterministic", "array-validation", name],
        "metadata": {"workflow": name, "external_run_id": run_id},
    }
    for record in graph.stream(
        initial_state,
        config=config,
        stream_mode=list(STREAM_MODES),
        version="v2",
    ):
        serialized = _json_safe(record)
        if not isinstance(serialized, dict):
            raise TypeError("LangGraph v2 stream record must serialize to an object")
        native_stream.append(serialized)
        if serialized.get("type") == "values" and isinstance(serialized.get("data"), dict):
            final_state = serialized["data"]
    canonical_trace = normalize_stream(
        native_stream,
        workflow=name,
        run_id=run_id,
        langgraph_version=installed_version,
    )
    return {
        "workflow": name,
        "run_id": run_id,
        "langgraph_version": installed_version,
        "stream_version": "v2",
        "stream_modes": list(STREAM_MODES),
        "native_stream": native_stream,
        "canonical_trace": canonical_trace,
        "final_state": final_state,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow",
        choices=["all", *available_workflows()],
        default="all",
        help="workflow to execute (default: all)",
    )
    parser.add_argument("--run-id", default="deterministic-demo")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON output path; stdout is used when omitted",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    names = available_workflows() if args.workflow == "all" else (args.workflow,)
    results = [run_workflow(name, f"{args.run_id}-{name}") for name in names]
    document: Any = results if args.workflow == "all" else results[0]
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
