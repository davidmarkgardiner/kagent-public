"""Offline regression tests for the Python shipped in the collector ConfigMap."""

import sys
import textwrap
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


COLLECTOR = Path(__file__).with_name("02-collector-configmap.yaml")
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def load_collector():
    # Execute the checked-in ConfigMap payload, not a duplicate of its logic.
    marker = "  collect.py: |\n"
    yaml = COLLECTOR.read_text(encoding="utf-8")
    if yaml.count(marker) != 1:
        raise AssertionError("expected exactly one collect.py block")
    payload = yaml.split(marker, 1)[1]
    if any(line and not line.startswith("    ") for line in payload.splitlines()):
        raise AssertionError("unexpected content after collect.py block")
    module = types.ModuleType("sentinel_collector_under_test")
    exec(compile(textwrap.dedent(payload), str(COLLECTOR), "exec"), module.__dict__)
    return module


def event(reason, timestamp=None, **fields):
    return {
        "reason": reason,
        "message": reason + " message",
        "involvedObject": {"namespace": "app"},
        "lastTimestamp": None,
        **({"eventTime": timestamp} if timestamp is not None else {}),
        **fields,
    }


class EventWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collector = load_collector()

    def test_fractional_rfc3339_and_null_last_timestamp(self):
        c = self.collector
        self.assertEqual(
            c._parse_ts("2026-10-10T11:59:59.173860Z"),
            datetime(2026, 10, 10, 11, 59, 59, 173860, tzinfo=timezone.utc),
        )
        self.assertEqual(
            c._event_ts(event("Probe", "2026-10-10T11:59:59.173860Z")),
            datetime(2026, 10, 10, 11, 59, 59, 173860, tzinfo=timezone.utc),
        )

    def test_timestamp_fallback_and_precedence(self):
        c = self.collector
        cases = (
            (event("A", None, lastTimestamp="2026-10-10T11:58:00Z"), 58),
            (event("B", None, firstTimestamp="2026-10-10T11:57:00Z"), 57),
            (event("C", None, series={"lastObservedTime": "2026-10-10T11:56:00Z"}), 56),
            (event("D", "invalid", lastTimestamp="2026-10-10T11:55:00Z"), 55),
            (event("E", "2026-10-10T11:59:00Z", lastTimestamp="2026-10-10T10:00:00Z"), 59),
        )
        for item, minute in cases:
            with self.subTest(reason=item["reason"]):
                self.assertEqual(c._event_ts(item).minute, minute)
        self.assertIsNone(c._event_ts(event("Undated")))

    def test_warning_window_counts_only_dated_in_window_events(self):
        c = self.collector
        events = [
            event("Inside", "2026-10-10T11:59:00.173860Z"),
            event("Boundary", "2026-10-10T11:45:00Z"),
            event("Stale", "2026-10-10T11:44:59.999999Z"),
            event("Undated"),
            event("Malformed", "not-a-date"),
            event("PolicyViolation", "2026-10-10T11:58:00Z"),
            event("PolicyViolation", "2026-10-10T10:00:00Z"),
        ]

        def fake_api(path):
            self.assertEqual(path, "/api/v1/events?fieldSelector=type%3DWarning&limit=2000")
            return {"items": events}

        with patch.object(c, "api", side_effect=fake_api), patch.object(c, "_now", return_value=NOW):
            result = c.collect_events()
        self.assertEqual(result["warning_total"], 2)
        self.assertEqual(result["by_reason"], [
            {"reason": "Inside", "count": 1},
            {"reason": "Boundary", "count": 1},
        ])
        self.assertEqual(result["excluded_total"], 1)
        self.assertEqual(result["excluded"], [{"filter": "PolicyViolation", "count": 1}])
        self.assertEqual(result["undated"], 2)

    def test_failed_scheduling_window_counts_only_dated_in_window_events(self):
        c = self.collector
        events = [
            event("FailedScheduling", "2026-10-10T11:59:00.173860Z"),
            event("FailedScheduling", "2026-10-10T11:45:00Z"),
            event("FailedScheduling", "2026-10-10T11:44:59.999999Z"),
            event("FailedScheduling"),
            event("FailedScheduling", "bad-time"),
            event("FailedScheduling", None, lastTimestamp="2026-10-10T11:57:00Z"),
        ]

        def fake_api(path):
            self.assertEqual(path, "/api/v1/events?fieldSelector=reason%3DFailedScheduling&limit=500")
            return {"items": events}

        with patch.object(c, "api", side_effect=fake_api), patch.object(c, "_list_pods", return_value=[]), patch.object(c, "_now", return_value=NOW):
            result = c.collect_scheduling()
        self.assertEqual(result["pending_count"], 0)
        self.assertEqual(result["failed_scheduling_messages"], [
            {"message": "FailedScheduling message", "count": 3},
        ])


if __name__ == "__main__":
    unittest.main()
