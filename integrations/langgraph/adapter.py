"""Normalize LangGraph v2 stream records into checker-compatible events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .schema import CanonicalEvent, NativeEmission


class AdapterError(ValueError):
    """Raised when native telemetry cannot support a canonical event."""


def _required_text(emission: Mapping[str, Any], key: str) -> str:
    value = emission.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"native emission lacks non-empty {key!r}: {emission!r}")
    return value


def _canonical_writes(
    writes: Any,
    *,
    run_id: str,
    trace_id: str,
) -> list[dict[str, Any]]:
    if writes is None:
        return []
    if not isinstance(writes, list):
        raise AdapterError("native writes must be a list")
    normalized: list[dict[str, Any]] = []
    for native in writes:
        if not isinstance(native, Mapping):
            raise AdapterError("each native write must be an object")
        provenance = native.get("provenance")
        if not isinstance(provenance, Mapping) or not provenance:
            raise AdapterError("every native write requires explicit non-empty provenance")
        scope = _required_text(native, "namespace")
        key = _required_text(native, "address")
        canonical_provenance = deepcopy(dict(provenance))
        canonical_provenance.setdefault("run_id", run_id)
        canonical_provenance["trace"] = trace_id
        normalized.append(
            {
                "scope": scope,
                "key": key,
                "value": deepcopy(native.get("content")),
                "provenance": canonical_provenance,
            }
        )
    return normalized


def _normalize_emission(
    emission: NativeEmission,
    *,
    workflow: str,
    run_id: str,
    node: str,
    task_id: str | None,
    step: int,
    langgraph_version: str,
) -> CanonicalEvent:
    kind = _required_text(emission, "kind")
    trace_id = f"{run_id}:{step:03d}"
    framework: dict[str, Any] = {
        "name": "langgraph",
        "version": langgraph_version,
        "stream_version": "v2",
        "stream_mode": "updates",
        "workflow": workflow,
        "run_id": run_id,
        "node": node,
        "native_kind": kind,
    }
    if task_id is not None:
        framework["task_id"] = task_id
    event_id = emission.get("event_id")
    if isinstance(event_id, str) and event_id:
        framework["native_event_id"] = event_id

    event: CanonicalEvent = {
        "step": step,
        "trace": trace_id,
        "framework": framework,
    }
    if kind in {"route", "message"}:
        event["event"] = "handoff" if kind == "route" else "message"
        event["from"] = _required_text(emission, "actor")
        event["to"] = _required_text(emission, "recipient")
        event["payload"] = _required_text(emission, "payload")
    elif kind == "tool_invocation":
        event["event"] = "tool_call"
        event["agent"] = _required_text(emission, "actor")
        event["tool"] = _required_text(emission, "operation")
        inputs = emission.get("inputs", {})
        if not isinstance(inputs, Mapping):
            raise AdapterError("tool inputs must be an object")
        for key in ("query", "claim", "source"):
            if key in inputs:
                event[key] = deepcopy(inputs[key])
        event["tool_input"] = deepcopy(dict(inputs))
        event["writes"] = _canonical_writes(
            emission.get("writes", []), run_id=run_id, trace_id=trace_id
        )
    elif kind == "state_write":
        event["event"] = "shared_memory_update"
        event["agent"] = _required_text(emission, "actor")
        event["writes"] = _canonical_writes(
            emission.get("writes"), run_id=run_id, trace_id=trace_id
        )
        if not event["writes"]:
            raise AdapterError("state_write emission must contain at least one write")
    elif kind == "claim_certificate":
        event["event"] = "certify"
        event["agent"] = _required_text(emission, "actor")
        event["claim"] = _required_text(emission, "claim_id")
        event["source"] = _required_text(emission, "source_key")
    elif kind == "final_output":
        event["event"] = "answer"
        event["agent"] = _required_text(emission, "actor")
        claims = emission.get("supported_claims")
        if not isinstance(claims, list) or not all(isinstance(item, str) for item in claims):
            raise AdapterError("final_output supported_claims must be a list of strings")
        event["claims"] = list(claims)
        if isinstance(emission.get("payload"), str):
            event["payload"] = emission["payload"]
    else:
        raise AdapterError(f"unsupported native event kind {kind!r}")
    return event


def normalize_stream(
    native_stream: Sequence[Mapping[str, Any]],
    *,
    workflow: str,
    run_id: str,
    langgraph_version: str,
) -> list[CanonicalEvent]:
    """Translate emissions from actual v2 ``updates`` records.

    ``tasks`` records are used only to retain native task identity. ``values``
    records and state-only updates remain in the captured stream but do not
    create canonical resource events.
    """

    active_tasks: dict[str, list[str]] = defaultdict(list)
    canonical: list[CanonicalEvent] = []
    for record in native_stream:
        record_type = record.get("type")
        data = record.get("data")
        if record_type == "tasks" and isinstance(data, Mapping):
            name = data.get("name")
            task_id = data.get("id")
            if isinstance(name, str) and isinstance(task_id, str):
                if "input" in data:
                    active_tasks[name].append(task_id)
                elif "result" in data and active_tasks[name]:
                    active_tasks[name].pop(0)
            continue
        if record_type != "updates" or not isinstance(data, Mapping):
            continue
        for node, update in data.items():
            if not isinstance(node, str) or not isinstance(update, Mapping):
                raise AdapterError("LangGraph updates must map node names to objects")
            emissions = update.get("emissions", [])
            if not isinstance(emissions, list):
                raise AdapterError(f"node {node!r} emitted a non-list telemetry value")
            task_id = active_tasks[node][0] if active_tasks[node] else None
            for raw_emission in emissions:
                if not isinstance(raw_emission, Mapping):
                    raise AdapterError(f"node {node!r} emitted a non-object event")
                step = len(canonical) + 1
                canonical.append(
                    _normalize_emission(
                        dict(raw_emission),
                        workflow=workflow,
                        run_id=run_id,
                        node=node,
                        task_id=task_id,
                        step=step,
                        langgraph_version=langgraph_version,
                    )
                )
    if not canonical:
        raise AdapterError("native stream contained no canonicalizable node emissions")
    return canonical
