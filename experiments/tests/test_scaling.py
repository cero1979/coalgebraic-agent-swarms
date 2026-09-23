from __future__ import annotations

import json
import unittest

from experiments.mutations import DEFAULT_RULES_PATH
from experiments.scaling import DEFAULT_LENGTHS, benchmark_scaling, generate_valid_trace
from prototype.checker import check_trace


class ScalingExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))

    def test_default_length_inventory_and_trace_shape(self) -> None:
        self.assertEqual(DEFAULT_LENGTHS, (10, 100, 1_000, 5_000, 10_000))
        for length in DEFAULT_LENGTHS:
            with self.subTest(length=length):
                trace = generate_valid_trace(length, self.rules)
                self.assertEqual(len(trace), length)
                self.assertEqual(trace[-1]["step"], length)
                self.assertEqual(len({event["trace"] for event in trace}), length)

    def test_generated_trace_is_accepted(self) -> None:
        trace = generate_valid_trace(100, self.rules, trace_prefix="test-scale")
        result = check_trace(trace, self.rules)
        self.assertTrue(result["accepted"], result)

    def test_benchmark_reports_required_statistics(self) -> None:
        report = benchmark_scaling(
            check_trace,
            self.rules,
            lengths=(10,),
            repetitions=3,
            warmups=0,
        )
        sample = report["samples"][0]
        self.assertEqual(sample["events"], 10)
        self.assertEqual(sample["event_type_counts"], {"message": 5, "handoff": 5})
        self.assertEqual(sample["repetitions"], 3)
        self.assertGreater(sample["median_seconds"], 0)
        self.assertGreaterEqual(sample["iqr_seconds"], 0)
        self.assertGreater(sample["events_per_second"], 0)
        self.assertIn("python_version", report["environment"])
        self.assertIn("platform", report["environment"])
        self.assertIn("timer", report["environment"])
        self.assertIn("processor", report["environment"])
        self.assertIn("logical_cpu_count", report["environment"])
        self.assertIn("process_machine", report["environment"])
        self.assertIn("host_machine", report["environment"])
        self.assertIn("process_translated", report["environment"])
        if report["environment"]["process_translated"]:
            self.assertNotEqual(
                report["environment"]["process_machine"],
                report["environment"]["host_machine"],
            )
        self.assertTrue(report["environment"]["deterministic_inputs"])
        self.assertIsNone(report["environment"]["random_seed"])

    def test_invalid_benchmark_configuration(self) -> None:
        with self.assertRaises(ValueError):
            benchmark_scaling(check_trace, self.rules, lengths=(10,), repetitions=0)
        with self.assertRaises(ValueError):
            generate_valid_trace(-1, self.rules)


if __name__ == "__main__":
    unittest.main()
