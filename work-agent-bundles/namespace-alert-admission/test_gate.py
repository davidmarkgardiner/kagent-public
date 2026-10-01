"""Behavioral tests against a disposable real PostgreSQL database."""
import concurrent.futures
import copy
import json
import os
import threading
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from gate import Gate, KafkaPublisher, Policy, handler_for, identity, OwnerResolver
from render_vector import render

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def signal(n=0, namespace="apps", severity="warning", observed=NOW, reason="BackOff"):
    return {"schema_version": "observability.triage.v2", "cluster": "test-cluster",
            "namespace": namespace, "pod": f"app-{n}", "reason": reason,
            "severity": severity, "signal_kind": "event", "automation_allowed": False,
            "observed_timestamp": observed.isoformat(), "dedupe_key": identity(n),
            "delivery_key": identity(n, reason), "object_kind": "Pod", "event_count": 1,
            "evidence": {"event_summary": reason, "representative_log_lines": "example"}}


class RecordingProducer:
    def __init__(self):
        self.messages = []

    def check(self, row, policy, now, ceiling):
        matching = [m for m in self.messages if m[4:] == (row["cluster"], row["namespace"], str(row["local_day"]))]
        if any(m[3] == row["intent_id"] for m in matching): return "already-sent"
        return "full" if len(matching) >= ceiling else "available"

    def send(self, topic, key, payload, intent, cluster, namespace, day):
        self.messages.append((topic, key, payload, intent, cluster, namespace, day))


class GateTests(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ["TEST_DATABASE_URL"]
        self.policy = Policy("test-cluster", ("apps", "system"), mode="enforce",
                             limit=2, triage_topic="test-triage", digest_topic="test-digest")
        self.gate = Gate(self.dsn, self.policy, lambda p: ("Deployment", p["pod"], True))
        self.gate.initialize()
        with self.gate.connect() as db:
            db.execute("TRUNCATE admission_seen,admission_groups,admission_counts,admission_reports,admission_outbox,admission_budget,admission_binding")

    def drain(self, gate=None, producer=None, now=NOW):
        gate = gate or self.gate
        producer = producer or RecordingProducer()
        while gate.publish_one(producer, now):
            pass
        return producer

    def test_40_candidates_publish_two_and_keep_counts(self):
        for n in range(40):
            self.gate.ingest(signal(n), NOW)
        report = self.gate.report(NOW)
        self.assertEqual(report["received_records"], 40)
        self.assertEqual(report["deferred_total"], 38)
        self.assertEqual(report["namespace_selected"]["apps"], 2)
        self.assertTrue(report["candidates_truncated"])
        self.assertLessEqual(len(json.dumps(report).encode()), 32768)
        messages = self.drain().messages
        self.assertEqual(sum(m[0] == "test-triage" for m in messages), 2)
        self.assertEqual(sum(m[0] == "test-digest" for m in messages), 1)

    def test_replay_concurrency_and_restart_do_not_spend_extra(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda _: self.gate.ingest(signal(1), NOW), range(30)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda _: self.gate.report(NOW), range(20)))
        restarted = Gate(self.dsn, self.policy)
        restarted.report(NOW)
        report = restarted.report(NOW)
        self.assertEqual(report["received_records"], 1)
        producer = RecordingProducer()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(lambda _: self.drain(restarted, producer), range(5)))
        self.assertEqual(len(producer.messages), 2)
        self.assertEqual(len(set(m[3] for m in producer.messages)), 2)

    def test_replacement_pods_group_via_owner(self):
        gate = Gate(self.dsn, self.policy, lambda p: ("Deployment", "api", True))
        for n in range(40):
            gate.ingest(signal(n), NOW)
        report = gate.report(NOW)
        self.assertEqual(report["candidate_total"], 1)
        self.assertEqual(report["received_records"], 40)
        self.assertEqual(len(self.drain(gate).messages), 2)

    def test_new_critical_candidate_beats_early_noise(self):
        for n in range(20):
            self.gate.ingest(signal(n, observed=NOW-timedelta(hours=2)), NOW)
        self.gate.ingest(signal(99, severity="critical"), NOW)
        report = self.gate.report(NOW)
        self.assertEqual(report["candidates"][0]["owner_name"], "app-99")
        self.assertTrue(report["candidates"][0]["selected"])

    def test_shadow_never_publishes_even_with_previous_pending(self):
        self.gate.ingest(signal(), NOW)
        self.gate.report(NOW)
        shadow = Gate(self.dsn, Policy("test-cluster", ("apps", "system")))
        shadow.report(NOW)
        self.assertFalse(shadow.publish_one(RecordingProducer(), NOW))

    def test_limits_one_two_and_namespace_isolation(self):
        for n in range(10):
            self.gate.ingest(signal(n), NOW)
            self.gate.ingest(signal(n, namespace="system"), NOW)
        for limit in (1, 2):
            with self.gate.connect() as db:
                db.execute("TRUNCATE admission_reports,admission_outbox,admission_budget,admission_binding")
            gate = Gate(self.dsn, Policy("test-cluster", ("apps", "system"), mode="enforce",
                                        limit=limit, overrides={"system": 1}, triage_topic="test-triage"))
            report = gate.report(NOW)
            self.assertEqual(report["namespace_selected"], {"apps": limit, "system": 1})
            self.assertEqual(len(self.drain(gate).messages), limit+1)

    def test_policy_change_cannot_reset_daily_slots(self):
        for n in range(10):
            self.gate.ingest(signal(n), NOW)
        self.gate.report(NOW)
        changed = Gate(self.dsn, Policy("test-cluster", ("apps", "system"), mode="enforce",
                                       limit=1, triage_topic="test-triage"))
        changed.report(NOW)
        self.assertEqual(sum(m[0] == "test-triage" for m in self.drain(changed).messages), 1)

    def test_critical_has_no_bypass_and_invalid_limits_rejected(self):
        for n in range(10):
            self.gate.ingest(signal(n, namespace="system", severity="critical", reason="NodeNotReady"), NOW)
        self.assertEqual(self.drain().messages, [])
        report = self.gate.report(NOW)
        self.assertEqual(report["selected_total"], 2)
        self.assertEqual(sum(m[0] == "test-triage" for m in self.drain().messages), 2)
        for limit in (0, 3, True):
            with self.assertRaises(ValueError): Policy("test", ("apps",), limit=limit)
        with self.assertRaises(TypeError):
            Policy("test", ("apps",), urgent_topic="bypass")

    def test_final_publish_budget_caps_extra_outbox_intents(self):
        with self.gate.connect() as db:
            for n in range(12):
                self.gate.enqueue(db,str(n),"apps","routine",signal(n),"test-triage",NOW)
        self.assertEqual(len(self.drain().messages), 2)
        with self.gate.connect() as db:
            with self.assertRaises(ValueError):
                self.gate.enqueue(db,"bypass","apps","urgent",signal(),"test-triage",NOW)

    def test_unavailable_broker_history_fails_closed(self):
        class Unavailable(RecordingProducer):
            def check(self, *args): raise TimeoutError()
        self.gate.ingest(signal(), NOW)
        self.gate.report(NOW)
        producer=self.drain(producer=Unavailable())
        self.assertEqual(producer.messages, [])
        self.assertFalse(self.gate.publish_one(producer,NOW))

    def test_database_rollback_reconciles_retained_broker_records(self):
        for n in range(20): self.gate.ingest(signal(n), NOW)
        self.gate.report(NOW)
        producer = self.drain()
        with self.gate.connect() as db:
            db.execute("TRUNCATE admission_reports,admission_outbox,admission_budget,admission_binding")
        self.gate.report(NOW)
        self.drain(producer=producer)
        self.assertEqual(len(producer.messages), 3)

    def test_seven_virtual_days_sustained_critical_traffic_and_replay(self):
        producer = RecordingProducer()
        for day in range(7):
            now = NOW + timedelta(days=day)
            for n in range(40):
                payload = signal(day*100+n, severity="critical", observed=now)
                self.gate.ingest(payload, now)
                self.gate.ingest(payload, now)
            self.gate.report(now)
            restarted = Gate(self.dsn, self.policy)
            self.drain(restarted, producer, now)
            restarted.report(now)
            self.assertFalse(restarted.publish_one(producer, now))
            self.assertEqual(sum(m[0]=="test-triage" and m[6]==str(self.policy.local_day(now)) for m in producer.messages), 2)
        with self.assertRaises(RuntimeError): self.gate.report(NOW)

    def test_ambiguous_delivery_never_retries(self):
        class Ambiguous(RecordingProducer):
            def send(self, *args):
                super().send(*args)
                raise TimeoutError()
        self.gate.ingest(signal(), NOW)
        self.gate.report(NOW)
        producer = self.drain(producer=Ambiguous())
        self.assertEqual(len(producer.messages), 2)
        self.assertFalse(self.gate.publish_one(producer, NOW))
        with self.gate.connect() as db:
            statuses = db.execute("SELECT status FROM admission_outbox").fetchall()
        self.assertTrue(all(s["status"] == "unknown" for s in statuses))

    def test_previous_day_and_old_outbox_never_backfill(self):
        self.gate.ingest(signal(), NOW)
        self.gate.report(NOW)
        producer = self.drain(now=NOW+timedelta(days=1))
        self.assertEqual(len(producer.messages), 0)
        with self.assertRaises(RuntimeError): self.gate.report(NOW.replace(hour=9))

    def test_local_day_dst_and_rollover(self):
        p = self.policy
        self.assertEqual(str(p.local_day(datetime(2026,10,1,23,30,tzinfo=timezone.utc))), "2026-10-02")
        self.assertEqual(str(p.local_day(datetime(2026,10,25,0,30,tzinfo=timezone.utc))), "2026-10-25")
        self.assertEqual(str(p.local_day(datetime(2026,10,25,1,30,tzinfo=timezone.utc))), "2026-10-25")

    def test_reject_bad_scope_stale_timestamp_and_capacity(self):
        for payload in (signal(namespace="outside"), signal(observed=NOW-timedelta(days=2)),
                        signal(observed=NOW+timedelta(hours=1))):
            with self.assertRaises(ValueError):
                self.gate.ingest(payload, NOW)
        gate = Gate(self.dsn, Policy("test-cluster", ("apps",), max_groups=1))
        gate.ingest(signal(1), NOW)
        with self.assertRaises(RuntimeError):
            gate.ingest(signal(2), NOW)
        with gate.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM admission_seen").fetchone()["n"], 1)

    def test_http_auth_and_json_framing(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.gate, "test-key"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            payload = signal(observed=datetime.now(timezone.utc))
            req = Request(f"http://127.0.0.1:{server.server_port}/signals", data=(json.dumps(payload)+"\n").encode())
            with self.assertRaises(HTTPError) as error:
                urlopen(req)
            self.assertEqual(error.exception.code, 401)
            req.add_header("Authorization", "Bearer test-key")
            with urlopen(req) as response:
                self.assertTrue(json.load(response)["accepted"])
        finally:
            server.shutdown()
            server.server_close()

    def test_vector_cutover_removes_all_direct_kafka_sinks(self):
        import yaml
        source = yaml.safe_dump_all([
            {"kind": "ConfigMap", "data": {"vector.yaml": yaml.safe_dump({"transforms": {"incident_signals": {}},
             "sinks": {"kafka": {"type": "kafka"}, "metrics": {"type": "prometheus_exporter"}}})}},
            {"kind": "Deployment", "spec": {"template": {"spec": {"containers": [{"name": "vector"}]}}}}])
        docs = list(yaml.safe_load_all(render(source, "http://admission:8080/signals", cutover=True)))
        config = yaml.safe_load(docs[0]["data"]["vector.yaml"])
        self.assertNotIn("kafka", config["sinks"])
        self.assertEqual(config["sinks"]["admission"]["inputs"], ["incident_signals"])
        shadow = list(yaml.safe_load_all(render(source, "http://admission:8080/signals")))
        self.assertIn("kafka", yaml.safe_load(shadow[0]["data"]["vector.yaml"])["sinks"])

    def test_database_outage_does_not_acknowledge_intake(self):
        unavailable = Gate("postgresql://admission@127.0.0.1:1/admission", self.policy)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(unavailable, "test-key"))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            req = Request(f"http://127.0.0.1:{server.server_port}/signals",
                          data=json.dumps(signal(observed=datetime.now(timezone.utc))).encode(),
                          headers={"Authorization": "Bearer test-key"})
            with self.assertRaises(HTTPError) as error:
                urlopen(req)
            self.assertEqual(error.exception.code, 503)
        finally:
            server.shutdown()
            server.server_close()

    def test_owner_chain_uses_api_metadata(self):
        from pathlib import Path
        resolver = OwnerResolver.__new__(OwnerResolver)
        resolver.base, resolver.sa, resolver.context = "https://api.example.invalid", Path("/test-sa"), None
        objects = [
            {"metadata": {"ownerReferences": [{"kind": "ReplicaSet", "name": "api-rs", "controller": True}]}},
            {"metadata": {"ownerReferences": [{"kind": "Deployment", "name": "api", "controller": True}]}},
            {"metadata": {}},
        ]
        class Response:
            def __init__(self, obj): self.obj = obj
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return json.dumps(self.obj).encode()
        with patch("gate.urlopen", side_effect=[Response(o) for o in objects]) as opener, \
                patch("gate.Path.read_text", return_value="synthetic"):
            self.assertEqual(resolver(signal()), ("Deployment", "api", True))
            self.assertEqual(opener.call_count, 3)
            self.assertTrue(opener.call_args.args[0].full_url.endswith("/deployments/api"))

    def test_retention_is_bounded_without_historical_budget_refund(self):
        self.gate.ingest(signal(),NOW)
        self.gate.report(NOW)
        self.drain()
        later=NOW+timedelta(days=32)
        self.gate.report(later)
        self.gate.prune(later)
        with self.gate.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM admission_seen").fetchone()["n"],0)
            self.assertEqual(db.execute("SELECT count(*) AS n FROM admission_budget").fetchone()["n"],0)
            self.assertEqual(db.execute("SELECT count(*) AS n FROM admission_outbox WHERE local_day < %s",(self.policy.local_day(later),)).fetchone()["n"],0)
        with self.assertRaises(RuntimeError): self.gate.report(NOW)

    def test_tls_required_for_normal_kafka_publisher(self):
        with patch.dict(os.environ, {"KAFKA_SECURITY_CONFIG": "{}"}):
            with self.assertRaises(ValueError):
                KafkaPublisher()


if __name__ == "__main__":
    unittest.main(verbosity=2)
