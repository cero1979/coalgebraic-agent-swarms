"""Valid trace generation and in-memory scaling benchmarks for E4."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


Trace = list[dict[str, Any]]
Rules = dict[str, Any]
Checker = Callable[[Trace, Rules], Mapping[str, Any]]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = REPOSITORY_ROOT / "prototype" / "rules.json"
DEFAULT_LENGTHS = (10, 100, 1_000, 5_000, 10_000)


@dataclass(frozen=True)
class ScalingSample:
    events: int
    durations_seconds: tuple[float, ...]

    def as_record(self) -> dict[str, Any]:
        ordered = sorted(self.durations_seconds)
        median = statistics.median(ordered)
        q1 = _percentile(ordered, 0.25)
        q3 = _percentile(ordered, 0.75)
        return {
            "events": self.events,
            "event_type_counts": {
                "message": (self.events + 1) // 2,
                "handoff": self.events // 2,
            },
            "repetitions": len(ordered),
            "durations_seconds": ordered,
            "median_seconds": median,
            "q1_seconds": q1,
            "q3_seconds": q3,
            "iqr_seconds": q3 - q1,
            "events_per_second": self.events / median if median > 0 else float("inf"),
        }


def _percentile(ordered: Sequence[float], probability: float) -> float:
    if not ordered:
        raise ValueError("at least one observation is required")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def load_rules(path: Path = DEFAULT_RULES_PATH) -> Rules:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def generate_valid_trace(length: int, rules: Rules, *, trace_prefix: str = "scale") -> Trace:
    """Generate an exact-length valid trace using only graph-safe communication."""

    if length < 0:
        raise ValueError("length must be non-negative")
    agents = list(rules.get("agents", []))
    if not agents and length:
        raise ValueError("rules must contain at least one agent")
    edges = [
        (source, target)
        for source in agents
        for target in rules.get("interaction_graph", {}).get(source, [])
        if target in agents
    ]
    trace: Trace = []
    for offset in range(length):
        step = offset + 1
        trace_id = f"{trace_prefix}-{step:08d}"
        if edges:
            source, target = edges[offset % len(edges)]
            event_type = "message" if offset % 2 == 0 else "handoff"
            event = {
                "step": step,
                "event": event_type,
                "from": source,
                "to": target,
                "payload": f"scaling payload {step}",
                "trace": trace_id,
            }
        else:
            event = {
                "step": step,
                "event": "answer",
                "agent": agents[0],
                "claims": [],
                "trace": trace_id,
            }
        trace.append(event)
    return trace


def environment_metadata() -> dict[str, Any]:
    """Capture the environment needed to interpret timing measurements."""

    system = platform.system()
    process_machine = platform.machine()
    host_machine = process_machine
    process_translated: bool | None = None
    try:
        host_machine = subprocess.run(
            ["uname", "-m"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip() or process_machine
    except (OSError, subprocess.CalledProcessError):
        pass
    if system == "Darwin":
        try:
            translated_value = subprocess.run(
                ["sysctl", "-in", "sysctl.proc_translated"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            process_translated = translated_value == "1"
        except (OSError, subprocess.CalledProcessError):
            process_translated = None
        if process_translated:
            try:
                host_machine = subprocess.run(
                    ["arch", "-arm64", "uname", "-m"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip() or "arm64"
            except (OSError, subprocess.CalledProcessError):
                host_machine = "arm64"

    processor = platform.processor().strip()
    if system == "Darwin":
        try:
            darwin_processor = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if darwin_processor:
                processor = darwin_processor
        except (OSError, subprocess.CalledProcessError):
            pass
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": system,
        "release": platform.release(),
        "platform": platform.platform(),
        "machine": process_machine,
        "process_machine": process_machine,
        "host_machine": host_machine,
        "process_translated": process_translated,
        "processor": processor or "unknown",
        "logical_cpu_count": os.cpu_count(),
        "timer": "time.perf_counter_ns",
        "random_seed": None,
        "deterministic_inputs": True,
    }


def benchmark_scaling(
    checker: Checker,
    rules: Rules,
    *,
    lengths: Sequence[int] = DEFAULT_LENGTHS,
    repetitions: int = 7,
    warmups: int = 1,
) -> dict[str, Any]:
    """Benchmark accepted traces and return median, IQR, throughput, and environment."""

    if repetitions < 1:
        raise ValueError("repetitions must be at least one")
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    samples: list[ScalingSample] = []
    for length in lengths:
        trace = generate_valid_trace(int(length), rules, trace_prefix=f"scale-{length}")
        validation = checker(copy.deepcopy(trace), copy.deepcopy(rules))
        if not validation.get("accepted", False):
            raise ValueError(f"generated trace of length {length} was rejected: {validation}")
        for _ in range(warmups):
            checker(copy.deepcopy(trace), copy.deepcopy(rules))
        durations: list[float] = []
        for _ in range(repetitions):
            candidate = copy.deepcopy(trace)
            active_rules = copy.deepcopy(rules)
            started = time.perf_counter_ns()
            result = checker(candidate, active_rules)
            elapsed = (time.perf_counter_ns() - started) / 1_000_000_000
            if not result.get("accepted", False):
                raise ValueError(f"generated trace of length {length} was rejected during timing")
            durations.append(elapsed)
        samples.append(ScalingSample(events=int(length), durations_seconds=tuple(durations)))
    return {
        "experiment": "E4_scaling",
        "workload": (
            "Accepted communication-only traces alternating message and handoff "
            "events over permitted graph edges, with unique audit identifiers."
        ),
        "lengths": [int(length) for length in lengths],
        "repetitions": repetitions,
        "warmups": warmups,
        "environment": environment_metadata(),
        "samples": [sample.as_record() for sample in samples],
    }


def _default_checker(trace: Trace, rules: Rules) -> Mapping[str, Any]:
    from prototype.checker import check_trace

    return check_trace(trace, rules)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the in-memory E4 scaling benchmark.")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)
    parser.add_argument("--lengths", nargs="+", type=int, default=list(DEFAULT_LENGTHS))
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    args = parser.parse_args(argv)
    report = benchmark_scaling(
        _default_checker,
        load_rules(args.rules),
        lengths=args.lengths,
        repetitions=args.repetitions,
        warmups=args.warmups,
    )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
