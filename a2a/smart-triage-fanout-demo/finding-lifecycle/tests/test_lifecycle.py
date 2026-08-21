from __future__ import annotations

import copy
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("finding_lifecycle", ROOT / "lifecycle.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def load_example(name: str = "canonical-finding.json") -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def with_run(payload: dict, run_id: str, observed: str | None = None) -> dict:
    result = copy.deepcopy(payload)
    result["runId"] = run_id
    if observed:
        result["observedAt"] = observed
        for evidence in result["evidence"]:
            evidence["observedAt"] = observed
    return result


class ContractTests(unittest.TestCase):
    def test_examples_validate_against_json_schema_and_runtime_contract(self):
        schema = json.loads((ROOT / "finding.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        for name in ("canonical-finding.json", "provisional-finding.json"):
            payload = load_example(name)
            validator.validate(payload)
            MODULE.validate_finding(payload)

    def test_same_workload_across_pod_recreation_has_one_fingerprint(self):
        first = load_example()
        second = with_run(first, "homelab-run-002")
        second["resource"]["observedResource"] = "checkout-api-9f6f7d-pq4st"
        self.assertEqual(MODULE.fingerprint(first), MODULE.fingerprint(second))

    def test_same_reason_on_different_cluster_has_different_fingerprint(self):
        first = load_example()
        second = with_run(first, "homelab-run-003")
        second["target"]["cluster"] = "another-demo-cluster"
        self.assertNotEqual(MODULE.fingerprint(first), MODULE.fingerprint(second))

    def test_credential_like_evidence_is_rejected(self):
        payload = load_example()
        payload["evidence"][0]["reference"] = "Authorization: Bearer example-token-value"
        with self.assertRaisesRegex(MODULE.ContractError, "credential-like"):
            MODULE.validate_finding(payload)

    def test_canonical_finding_requires_stable_workload(self):
        payload = load_example()
        payload["resource"]["stableWorkload"] = ""
        with self.assertRaisesRegex(MODULE.ContractError, "stableWorkload"):
            MODULE.validate_finding(payload)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MODULE.LifecycleStore(str(Path(self.temp.name) / "findings.db"))
        self.base = load_example()

    def tearDown(self):
        self.temp.cleanup()

    def test_new_ongoing_and_idempotent_replay(self):
        new = self.store.evaluate(self.base)
        self.assertEqual("NEW", new["status"])
        self.assertTrue(new["notify"])
        self.assertEqual("CREATE", new["ticketAction"])
        replay = self.store.evaluate(self.base)
        self.assertEqual("NEW", replay["status"])
        self.assertTrue(replay["idempotentReplay"])
        self.assertFalse(replay["notify"])
        self.assertFalse(replay["autoTicketAllowed"])
        self.assertEqual("NONE", replay["ticketAction"])
        ongoing = self.store.evaluate(with_run(self.base, "homelab-run-002", "2026-08-20T10:10:00Z"))
        self.assertEqual("ONGOING", ongoing["status"])
        self.assertFalse(ongoing["notify"])
        self.assertEqual("NONE", ongoing["ticketAction"])
        self.assertEqual(2, ongoing["timesSeen"])

    def test_escalation(self):
        self.store.evaluate(self.base)
        escalated = with_run(self.base, "homelab-run-critical", "2026-08-20T10:10:00Z")
        escalated["finding"]["severity"] = "critical"
        decision = self.store.evaluate(escalated)
        self.assertEqual("ESCALATED", decision["status"])
        self.assertEqual("warning", decision["previousSeverity"])
        self.assertTrue(decision["notify"])
        self.assertEqual("CREATE", decision["ticketAction"])

    def test_resolution_and_recurrence(self):
        self.store.evaluate(self.base)
        resolved = with_run(self.base, "homelab-run-resolved", "2026-08-20T10:20:00Z")
        resolved["observationStatus"] = "resolved"
        self.assertEqual("RESOLVED", self.store.evaluate(resolved)["status"])
        recurrence = with_run(self.base, "homelab-run-recurrence", "2026-08-20T10:30:00Z")
        decision = self.store.evaluate(recurrence)
        self.assertEqual("RECURRENT", decision["status"])
        self.assertTrue(decision["notify"])

    def test_acknowledgement_suppresses_notification_without_deleting_history(self):
        decision = self.store.evaluate(self.base)
        until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        ack = self.store.acknowledge({
            "fingerprint": decision["fingerprint"], "actor": "sre-reviewer", "ackUntil": until,
        })
        self.assertEqual("ACKNOWLEDGED", ack["status"])
        repeat = self.store.evaluate(with_run(self.base, "homelab-run-after-ack", "2026-08-20T10:40:00Z"))
        self.assertEqual("ACKNOWLEDGED", repeat["status"])
        self.assertFalse(repeat["notify"])
        rows = self.store.list_findings()["findings"]
        self.assertEqual(2, rows[0]["times_seen"])

    def test_expired_acknowledgement_no_longer_sets_acknowledged_status(self):
        decision = self.store.evaluate(self.base)
        until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        self.store.acknowledge({
            "fingerprint": decision["fingerprint"], "actor": "sre-reviewer", "ackUntil": until,
        })
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE findings SET ack_until=? WHERE fingerprint=?",
                ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), decision["fingerprint"]),
            )
        repeat = self.store.evaluate(with_run(self.base, "homelab-run-after-expired-ack", "2026-08-20T10:40:00Z"))
        self.assertEqual("ONGOING", repeat["status"])

    def test_linked_issue_is_retained_but_unchanged_finding_does_not_request_update(self):
        decision = self.store.evaluate(self.base)
        linked = self.store.link_issue({
            "fingerprint": decision["fingerprint"],
            "issueUrl": "https://gitlab.example.invalid/platform/incidents/-/issues/85",
            "actor": "ticket-workflow",
        })
        self.assertEqual("LINKED", linked["status"])
        ongoing = self.store.evaluate(with_run(self.base, "homelab-run-linked-ongoing", "2026-08-20T10:10:00Z"))
        self.assertEqual("ONGOING", ongoing["status"])
        self.assertFalse(ongoing["autoTicketAllowed"])
        self.assertEqual("NONE", ongoing["ticketAction"])
        escalated = with_run(self.base, "homelab-run-linked-escalated", "2026-08-20T10:20:00Z")
        escalated["finding"]["severity"] = "critical"
        escalation = self.store.evaluate(escalated)
        self.assertEqual("UPDATE", escalation["ticketAction"])
        row = self.store.list_findings()["findings"][0]
        self.assertEqual(linked["issueUrl"], row["canonical_issue_url"])

    def test_provisional_finding_is_not_persisted_or_auto_ticketed(self):
        provisional = load_example("provisional-finding.json")
        decision = self.store.evaluate(provisional)
        self.assertEqual("PROVISIONAL", decision["status"])
        self.assertFalse(decision["autoTicketAllowed"])
        self.assertEqual([], self.store.list_findings()["findings"])

    def test_complete_snapshot_marks_absent_finding_resolved(self):
        first = self.store.evaluate(self.base)
        report = {
            "reportId": "snapshot-001",
            "observedAt": "2026-08-20T11:00:00Z",
            "subscriptionScope": "homelab",
            "cluster": "demo-cluster",
            "domains": ["pod-health"],
            "findings": [],
            "completeSnapshot": True,
        }
        result = self.store.snapshot(report)
        self.assertEqual(first["fingerprint"], result["resolved"][0]["fingerprint"])
        self.assertEqual("RESOLVED", result["resolved"][0]["status"])

    def test_stale_snapshot_does_not_resolve_newer_finding(self):
        latest = with_run(self.base, "latest-before-snapshot", "2026-08-20T12:00:00Z")
        first = self.store.evaluate(latest)
        result = self.store.snapshot({
            "reportId": "snapshot-stale",
            "observedAt": "2026-08-20T11:00:00Z",
            "subscriptionScope": "homelab",
            "cluster": "demo-cluster",
            "domains": ["pod-health"],
            "findings": [],
            "completeSnapshot": True,
        })
        self.assertEqual([], result["resolved"])
        self.assertEqual(first["fingerprint"], result["stale"][0]["fingerprint"])
        row = self.store.list_findings()["findings"][0]
        self.assertIsNone(row["resolved_at"])
        self.assertEqual("2026-08-20T12:00:00+00:00", row["last_seen"])

    def test_run_id_reuse_with_changed_payload_is_rejected(self):
        self.store.evaluate(self.base)
        changed = copy.deepcopy(self.base)
        changed["finding"]["summary"] = "A conflicting payload for the same run."
        with self.assertRaisesRegex(MODULE.ContractError, "different payload"):
            self.store.evaluate(changed)

    def test_out_of_order_observation_does_not_regress_state(self):
        latest = with_run(self.base, "latest-run", "2026-08-20T12:00:00Z")
        self.store.evaluate(latest)
        stale = with_run(self.base, "stale-run", "2026-08-20T11:00:00Z")
        decision = self.store.evaluate(stale)
        self.assertEqual("STALE", decision["status"])
        self.assertFalse(decision["notify"])
        row = self.store.list_findings()["findings"][0]
        self.assertEqual("2026-08-20T12:00:00+00:00", row["last_seen"])
        self.assertEqual(1, row["times_seen"])

    def test_state_failure_raises_instead_of_falling_back_to_memory(self):
        with mock.patch.object(self.store, "_connect", side_effect=sqlite3.OperationalError("state unavailable")):
            with self.assertRaisesRegex(sqlite3.OperationalError, "state unavailable"):
                self.store.evaluate(self.base)


if __name__ == "__main__":
    unittest.main()
