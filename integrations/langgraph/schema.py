"""Typed schemas shared by the deterministic LangGraph integration."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


PINNED_LANGGRAPH_VERSION = "1.2.11"
WorkflowName = Literal["research", "resource_controlled", "shared_memory"]
NativeEventKind = Literal[
    "route",
    "message",
    "tool_invocation",
    "state_write",
    "claim_certificate",
    "final_output",
]


class NativeWrite(TypedDict):
    """Application telemetry for a state write returned by a graph node."""

    namespace: Literal["shared", "local"]
    address: str
    content: Any
    provenance: dict[str, Any]


class NativeEmission(TypedDict, total=False):
    """Domain telemetry carried inside a real LangGraph node update."""

    kind: NativeEventKind
    event_id: str
    actor: str
    recipient: str
    payload: str
    operation: str
    inputs: dict[str, Any]
    writes: list[NativeWrite]
    claim_id: str
    source_key: str
    supported_claims: list[str]


class WorkflowState(TypedDict, total=False):
    """State shared by all three deterministic StateGraph workflows."""

    workflow: WorkflowName
    run_id: str
    query: str
    shared_memory: dict[str, Any]
    remaining_budgets: dict[str, int]
    certified_claims: Annotated[list[str], operator.add]
    emissions: Annotated[list[NativeEmission], operator.add]
    route: str
    answer: str


CanonicalEvent = dict[str, Any]


class WorkflowRun(TypedDict):
    """Stable public result returned by :func:`run_workflow`."""

    workflow: WorkflowName
    run_id: str
    langgraph_version: str
    stream_version: Literal["v2"]
    stream_modes: list[str]
    native_stream: list[dict[str, Any]]
    canonical_trace: list[CanonicalEvent]
    final_state: dict[str, Any]
