"""Deterministic workflows that execute through LangGraph StateGraph."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from langgraph.graph import END, START, StateGraph

from .schema import NativeEmission, NativeWrite, WorkflowName, WorkflowState


INITIAL_BUDGETS = {"Planner": 3, "Retriever": 5, "Verifier": 2}


def _event_id(state: WorkflowState, node: str, label: str) -> str:
    return f"{state['run_id']}:{node}:{label}"


def _provenance(
    state: WorkflowState,
    *,
    node: str,
    agent: str,
    operation: str,
    origin: str,
    derived_from: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "framework": "langgraph",
        "workflow": state["workflow"],
        "run_id": state["run_id"],
        "node": node,
        "agent": agent,
        "operation": operation,
        "origin": origin,
    }
    if derived_from:
        record["derived_from"] = list(derived_from)
    return record


def _write(
    state: WorkflowState,
    *,
    node: str,
    agent: str,
    operation: str,
    key: str,
    value: Any,
    origin: str,
    derived_from: list[str] | None = None,
) -> NativeWrite:
    return {
        "namespace": "shared",
        "address": key,
        "content": value,
        "provenance": _provenance(
            state,
            node=node,
            agent=agent,
            operation=operation,
            origin=origin,
            derived_from=derived_from,
        ),
    }


def _bibliographic_search(query: str, source_key: str) -> str:
    """Deterministic local tool; no model, network, or commercial API is used."""

    catalogue = {
        "src_research_coalgebra": "Rutten (2000), Universal coalgebra: a theory of systems",
        "src_budget_sell": "Nigam and Miller (2009), Algorithmic specifications in linear logic with subexponentials",
        "src_budget_sessions": "Caires and Pfenning (2010), Session types as intuitionistic linear propositions",
        "src_shared_raw": "W3C PROV-DM provenance record for an append-only source",
    }
    result = catalogue[source_key]
    return f"{result}; deterministic query={query!r}"


def _claim_check(claim: str, source_value: str) -> bool:
    """Deterministic structural check used to exercise the Verifier tool path."""

    return bool(claim.strip() and source_value.strip())


def _initial_state(name: WorkflowName, run_id: str) -> WorkflowState:
    queries: dict[WorkflowName, str] = {
        "research": "coalgebraic behavioural equivalence for agent systems",
        "resource_controlled": "linear resources in agent protocols",
        "shared_memory": "provenance for shared agent memory",
    }
    return {
        "workflow": name,
        "run_id": run_id,
        "query": queries[name],
        "shared_memory": {},
        "remaining_budgets": deepcopy(INITIAL_BUDGETS),
        "certified_claims": [],
        "emissions": [],
        "route": "",
        "answer": "",
    }


def _research_graph() -> Any:
    graph = StateGraph(WorkflowState)

    def planner(state: WorkflowState) -> dict[str, Any]:
        node = "research_planner"
        event: NativeEmission = {
            "kind": "route",
            "event_id": _event_id(state, node, "retrieve"),
            "actor": "Planner",
            "recipient": "Retriever",
            "payload": "retrieve a source for the requested coalgebraic claim",
        }
        return {"emissions": [event]}

    def retriever(state: WorkflowState) -> dict[str, Any]:
        node = "research_retriever"
        key = "src_research_coalgebra"
        result = _bibliographic_search(state["query"], key)
        write = _write(
            state,
            node=node,
            agent="Retriever",
            operation="BibliographicSearch",
            key=key,
            value=result,
            origin="deterministic_tool_result",
        )
        memory = dict(state["shared_memory"])
        memory[key] = result
        budgets = dict(state["remaining_budgets"])
        budgets["Retriever"] -= 2
        events: list[NativeEmission] = [
            {
                "kind": "tool_invocation",
                "event_id": _event_id(state, node, "search"),
                "actor": "Retriever",
                "operation": "BibliographicSearch",
                "inputs": {"query": state["query"]},
                "writes": [write],
            },
            {
                "kind": "message",
                "event_id": _event_id(state, node, "notify-verifier"),
                "actor": "Retriever",
                "recipient": "Verifier",
                "payload": f"verify the candidate source {key}",
            },
        ]
        return {
            "shared_memory": memory,
            "remaining_budgets": budgets,
            "emissions": events,
        }

    def verifier(state: WorkflowState) -> dict[str, Any]:
        node = "research_verifier"
        key = "src_research_coalgebra"
        claim = "coalgebra_behavioural_equivalence"
        claim_text = "Coalgebra supports behavioural equivalence for state-based systems"
        if not _claim_check(claim_text, state["shared_memory"][key]):
            raise RuntimeError("deterministic ClaimCheck unexpectedly failed")
        budgets = dict(state["remaining_budgets"])
        budgets["Verifier"] -= 1
        events: list[NativeEmission] = [
            {
                "kind": "tool_invocation",
                "event_id": _event_id(state, node, "check"),
                "actor": "Verifier",
                "operation": "ClaimCheck",
                "inputs": {"claim": claim_text, "source": key},
                "writes": [],
            },
            {
                "kind": "claim_certificate",
                "event_id": _event_id(state, node, "certify"),
                "actor": "Verifier",
                "claim_id": claim,
                "source_key": key,
            },
            {
                "kind": "route",
                "event_id": _event_id(state, node, "return"),
                "actor": "Verifier",
                "recipient": "Planner",
                "payload": "return the certified research claim",
            },
        ]
        return {
            "remaining_budgets": budgets,
            "certified_claims": [claim],
            "emissions": events,
        }

    def answer(state: WorkflowState) -> dict[str, Any]:
        node = "research_answer"
        claims = list(state["certified_claims"])
        text = "The retrieved source supports the certified coalgebraic claim."
        event: NativeEmission = {
            "kind": "final_output",
            "event_id": _event_id(state, node, "answer"),
            "actor": "Planner",
            "supported_claims": claims,
            "payload": text,
        }
        return {"answer": text, "emissions": [event]}

    graph.add_node("research_planner", planner)
    graph.add_node("research_retriever", retriever)
    graph.add_node("research_verifier", verifier)
    graph.add_node("research_answer", answer)
    graph.add_edge(START, "research_planner")
    graph.add_edge("research_planner", "research_retriever")
    graph.add_edge("research_retriever", "research_verifier")
    graph.add_edge("research_verifier", "research_answer")
    graph.add_edge("research_answer", END)
    return graph.compile(name="deterministic-research-swarm")


def _resource_graph() -> Any:
    graph = StateGraph(WorkflowState)

    def planner(state: WorkflowState) -> dict[str, Any]:
        node = "resource_planner"
        event: NativeEmission = {
            "kind": "route",
            "event_id": _event_id(state, node, "retrieve"),
            "actor": "Planner",
            "recipient": "Retriever",
            "payload": "collect two sources while respecting the retrieval budget",
        }
        return {"emissions": [event]}

    def search(state: WorkflowState, *, node: str, key: str) -> dict[str, Any]:
        if state["remaining_budgets"]["Retriever"] < 2:
            raise RuntimeError("workflow attempted a search without local budget")
        result = _bibliographic_search(state["query"], key)
        write = _write(
            state,
            node=node,
            agent="Retriever",
            operation="BibliographicSearch",
            key=key,
            value=result,
            origin="deterministic_tool_result",
        )
        memory = dict(state["shared_memory"])
        memory[key] = result
        budgets = dict(state["remaining_budgets"])
        budgets["Retriever"] -= 2
        event: NativeEmission = {
            "kind": "tool_invocation",
            "event_id": _event_id(state, node, "search"),
            "actor": "Retriever",
            "operation": "BibliographicSearch",
            "inputs": {"query": state["query"], "source_key": key},
            "writes": [write],
        }
        return {
            "shared_memory": memory,
            "remaining_budgets": budgets,
            "emissions": [event],
        }

    def search_primary(state: WorkflowState) -> dict[str, Any]:
        return search(state, node="resource_search_primary", key="src_budget_sell")

    def budget_gate(state: WorkflowState) -> dict[str, Any]:
        route = "search_again" if state["remaining_budgets"]["Retriever"] >= 2 else "verify"
        return {"route": route}

    def search_secondary(state: WorkflowState) -> dict[str, Any]:
        update = search(
            state,
            node="resource_search_secondary",
            key="src_budget_sessions",
        )
        update["emissions"].append(
            {
                "kind": "message",
                "event_id": _event_id(state, "resource_search_secondary", "notify-verifier"),
                "actor": "Retriever",
                "recipient": "Verifier",
                "payload": "two budgeted sources are ready for verification",
            }
        )
        return update

    def verifier(state: WorkflowState) -> dict[str, Any]:
        node = "resource_verifier"
        source = "src_budget_sell"
        claim = "sell_controls_linear_resources"
        claim_text = "SELL subexponentials distinguish reusable and linear resources"
        if not _claim_check(claim_text, state["shared_memory"][source]):
            raise RuntimeError("deterministic ClaimCheck unexpectedly failed")
        budgets = dict(state["remaining_budgets"])
        budgets["Verifier"] -= 1
        events: list[NativeEmission] = [
            {
                "kind": "tool_invocation",
                "event_id": _event_id(state, node, "check"),
                "actor": "Verifier",
                "operation": "ClaimCheck",
                "inputs": {"claim": claim_text, "source": source},
                "writes": [],
            },
            {
                "kind": "claim_certificate",
                "event_id": _event_id(state, node, "certify"),
                "actor": "Verifier",
                "claim_id": claim,
                "source_key": source,
            },
            {
                "kind": "route",
                "event_id": _event_id(state, node, "return"),
                "actor": "Verifier",
                "recipient": "Planner",
                "payload": "return the resource-certified claim",
            },
        ]
        return {
            "remaining_budgets": budgets,
            "certified_claims": [claim],
            "emissions": events,
        }

    def answer(state: WorkflowState) -> dict[str, Any]:
        node = "resource_answer"
        text = "The workflow completed within the explicit tool budgets."
        event: NativeEmission = {
            "kind": "final_output",
            "event_id": _event_id(state, node, "answer"),
            "actor": "Planner",
            "supported_claims": list(state["certified_claims"]),
            "payload": text,
        }
        return {"answer": text, "emissions": [event]}

    graph.add_node("resource_planner", planner)
    graph.add_node("resource_search_primary", search_primary)
    graph.add_node("resource_budget_gate", budget_gate)
    graph.add_node("resource_search_secondary", search_secondary)
    graph.add_node("resource_verifier", verifier)
    graph.add_node("resource_answer", answer)
    graph.add_edge(START, "resource_planner")
    graph.add_edge("resource_planner", "resource_search_primary")
    graph.add_edge("resource_search_primary", "resource_budget_gate")
    graph.add_conditional_edges(
        "resource_budget_gate",
        lambda state: state["route"],
        {"search_again": "resource_search_secondary", "verify": "resource_verifier"},
    )
    graph.add_edge("resource_search_secondary", "resource_verifier")
    graph.add_edge("resource_verifier", "resource_answer")
    graph.add_edge("resource_answer", END)
    return graph.compile(name="deterministic-resource-controlled")


def _shared_memory_graph() -> Any:
    graph = StateGraph(WorkflowState)

    def planner(state: WorkflowState) -> dict[str, Any]:
        node = "memory_planner"
        event: NativeEmission = {
            "kind": "route",
            "event_id": _event_id(state, node, "collect"),
            "actor": "Planner",
            "recipient": "Retriever",
            "payload": "collect a provenance-bearing shared source",
        }
        return {"emissions": [event]}

    def collector(state: WorkflowState) -> dict[str, Any]:
        node = "memory_collector"
        key = "src_shared_raw"
        result = _bibliographic_search(state["query"], key)
        write = _write(
            state,
            node=node,
            agent="Retriever",
            operation="BibliographicSearch",
            key=key,
            value=result,
            origin="deterministic_tool_result",
        )
        memory = dict(state["shared_memory"])
        memory[key] = result
        budgets = dict(state["remaining_budgets"])
        budgets["Retriever"] -= 2
        events: list[NativeEmission] = [
            {
                "kind": "tool_invocation",
                "event_id": _event_id(state, node, "search"),
                "actor": "Retriever",
                "operation": "BibliographicSearch",
                "inputs": {"query": state["query"]},
                "writes": [write],
            },
            {
                "kind": "message",
                "event_id": _event_id(state, node, "notify-verifier"),
                "actor": "Retriever",
                "recipient": "Verifier",
                "payload": f"shared source {key} is ready for cross-component validation",
            },
        ]
        return {
            "shared_memory": memory,
            "remaining_budgets": budgets,
            "emissions": events,
        }

    def verifier_write(state: WorkflowState) -> dict[str, Any]:
        node = "memory_verifier_write"
        raw_key = "src_shared_raw"
        verified_key = "src_shared_verified"
        claim_text = "Append-only memory retains a derivation link to the source"
        raw_value = state["shared_memory"][raw_key]
        if not _claim_check(claim_text, raw_value):
            raise RuntimeError("deterministic ClaimCheck unexpectedly failed")
        verified_value = f"structurally checked from {raw_key}: {raw_value}"
        write = _write(
            state,
            node=node,
            agent="Verifier",
            operation="ClaimCheck",
            key=verified_key,
            value=verified_value,
            origin="derived_shared_memory_record",
            derived_from=[raw_key],
        )
        memory = dict(state["shared_memory"])
        memory[verified_key] = verified_value
        budgets = dict(state["remaining_budgets"])
        budgets["Verifier"] -= 1
        events: list[NativeEmission] = [
            {
                "kind": "tool_invocation",
                "event_id": _event_id(state, node, "check"),
                "actor": "Verifier",
                "operation": "ClaimCheck",
                "inputs": {"claim": claim_text, "source": raw_key},
                "writes": [],
            },
            {
                "kind": "state_write",
                "event_id": _event_id(state, node, "derive"),
                "actor": "Verifier",
                "writes": [write],
            },
        ]
        return {
            "shared_memory": memory,
            "remaining_budgets": budgets,
            "emissions": events,
        }

    def verifier_certify(state: WorkflowState) -> dict[str, Any]:
        node = "memory_verifier_certify"
        claim = "shared_memory_provenance_is_auditable"
        source = "src_shared_verified"
        if source not in state["shared_memory"]:
            raise RuntimeError("derived shared-memory source is unavailable")
        events: list[NativeEmission] = [
            {
                "kind": "claim_certificate",
                "event_id": _event_id(state, node, "certify"),
                "actor": "Verifier",
                "claim_id": claim,
                "source_key": source,
            },
            {
                "kind": "route",
                "event_id": _event_id(state, node, "return"),
                "actor": "Verifier",
                "recipient": "Planner",
                "payload": "return the claim supported by derived shared memory",
            },
        ]
        return {"certified_claims": [claim], "emissions": events}

    def answer(state: WorkflowState) -> dict[str, Any]:
        node = "memory_answer"
        text = "The answer cites a claim backed by a provenance-bearing shared record."
        event: NativeEmission = {
            "kind": "final_output",
            "event_id": _event_id(state, node, "answer"),
            "actor": "Planner",
            "supported_claims": list(state["certified_claims"]),
            "payload": text,
        }
        return {"answer": text, "emissions": [event]}

    graph.add_node("memory_planner", planner)
    graph.add_node("memory_collector", collector)
    graph.add_node("memory_verifier_write", verifier_write)
    graph.add_node("memory_verifier_certify", verifier_certify)
    graph.add_node("memory_answer", answer)
    graph.add_edge(START, "memory_planner")
    graph.add_edge("memory_planner", "memory_collector")
    graph.add_edge("memory_collector", "memory_verifier_write")
    graph.add_edge("memory_verifier_write", "memory_verifier_certify")
    graph.add_edge("memory_verifier_certify", "memory_answer")
    graph.add_edge("memory_answer", END)
    return graph.compile(name="deterministic-shared-memory")


WORKFLOW_BUILDERS: dict[WorkflowName, Callable[[], Any]] = {
    "research": _research_graph,
    "resource_controlled": _resource_graph,
    "shared_memory": _shared_memory_graph,
}


def available_workflows() -> tuple[WorkflowName, ...]:
    """Return workflow names in stable CLI and experiment order."""

    return tuple(WORKFLOW_BUILDERS)


def build_workflow(name: WorkflowName, run_id: str) -> tuple[Any, WorkflowState]:
    """Compile one real StateGraph and construct its deterministic input state."""

    if name not in WORKFLOW_BUILDERS:
        raise ValueError(f"unknown workflow {name!r}; expected one of {available_workflows()}")
    if not run_id.strip():
        raise ValueError("run_id must be a non-empty string")
    return WORKFLOW_BUILDERS[name](), _initial_state(name, run_id)
