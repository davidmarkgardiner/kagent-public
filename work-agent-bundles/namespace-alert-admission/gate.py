"""Pre-Kafka evidence intake, daily selection and bounded publication.

No cluster or ticket writes. PostgreSQL holds authoritative state. A claimed
send is never automatically resent after an ambiguous outcome.
"""
import hashlib
import hmac
import json
import logging
import os
import re
import ssl
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

UTC = timezone.utc
SEVERITY = {"critical": 4, "error": 3, "warning": 2, "info": 1}
FIELDS = {
    "schema_version", "cluster", "namespace", "node", "pod", "container",
    "service", "reason", "severity", "signal_kind", "event_type", "object_kind",
    "event_count", "reporting_component", "source_type", "observed_timestamp",
    "dedupe_key", "delivery_key", "automation_allowed", "evidence", "scope",
}
LOG = logging.getLogger("admission")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def identity(*parts):
    return hashlib.sha256(canonical(parts).encode()).hexdigest()


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return result.astimezone(UTC)


@dataclass(frozen=True)
class Policy:
    cluster: str
    namespaces: tuple
    mode: str = "report-only"
    limit: int = 1
    overrides: dict = field(default_factory=dict)
    timezone_name: str = "Europe/London"
    report_hour: int = 9
    report_minute: int = 0
    triage_topic: str = ""
    digest_topic: str = ""
    max_groups: int = 10000

    def __post_init__(self):
        if self.mode not in ("report-only", "enforce"):
            raise ValueError("invalid mode")
        if type(self.limit) is not int or self.limit not in (1, 2) or any(type(v) is not int or v not in (1, 2) for v in self.overrides.values()):
            raise ValueError("namespace limits must be 1 or 2")
        if not self.cluster or not self.namespaces or len(self.namespaces)>100 or len(set(self.namespaces)) != len(self.namespaces):
            raise ValueError("explicit cluster and unique namespace allowlist required")
        if not set(self.overrides).issubset(self.namespaces):
            raise ValueError("override outside allowlist")
        if not 0 <= self.report_hour <= 23 or not 0 <= self.report_minute <= 59 or self.max_groups < 1:
            raise ValueError("invalid schedule or capacity")
        ZoneInfo(self.timezone_name)
        if self.mode == "enforce" and not self.triage_topic:
            raise ValueError("triage topic required")
        if self.digest_topic and self.digest_topic == self.triage_topic:
            raise ValueError("digest must use a separate topic")

    def local_day(self, now):
        return now.astimezone(ZoneInfo(self.timezone_name)).date()

    def due(self, now):
        local = now.astimezone(ZoneInfo(self.timezone_name))
        return (local.hour, local.minute) >= (self.report_hour, self.report_minute)


class OwnerResolver:
    """Resolve real owner references, not pod-name guesses. Bounded per call."""
    def __init__(self):
        self.base = "https://{}:{}".format(os.environ["KUBERNETES_SERVICE_HOST"],
                                          os.environ["KUBERNETES_SERVICE_PORT"])
        self.sa = Path("/var/run/secrets/kubernetes.io/serviceaccount")
        self.context = ssl.create_default_context(cafile=str(self.sa / "ca.crt"))

    def __call__(self, payload):
        kind = payload.get("object_kind") or "Pod"
        name = payload.get("pod", "")
        namespace = payload["namespace"]
        paths = {"Pod": "/api/v1", "ReplicaSet": "/apis/apps/v1",
                 "Deployment": "/apis/apps/v1", "StatefulSet": "/apis/apps/v1",
                 "DaemonSet": "/apis/apps/v1", "Job": "/apis/batch/v1",
                 "CronJob": "/apis/batch/v1"}
        plurals = {k: k.lower() + "s" for k in paths}
        if not name or kind not in paths:
            return kind or "Unknown", name or "unknown", False
        original = (kind, name)
        try:
            for _ in range(4):
                path = "{}/namespaces/{}/{}/{}".format(paths[kind], quote(namespace, safe=""),
                                                        plurals[kind], quote(name, safe=""))
                request = Request(self.base + path)
                request.add_header("Authorization", "Bearer " + (self.sa / "token").read_text().strip())
                with urlopen(request, context=self.context, timeout=2) as response:
                    obj = json.loads(response.read(256 * 1024))
                owners = [o for o in obj["metadata"].get("ownerReferences", []) if o.get("controller")]
                if not owners:
                    return kind, name, True
                owner = owners[0]
                if owner["kind"] not in paths:
                    return owner["kind"], owner["name"], True
                kind, name = owner["kind"], owner["name"]
        except Exception:
            LOG.warning("owner lookup unavailable; retaining unresolved identity")
        return *original, False


class Gate:
    def __init__(self, dsn, policy, resolver=None):
        self.dsn, self.policy = dsn, policy
        self.resolver = resolver or (lambda p: (p.get("object_kind") or "Pod", p.get("pod") or "unknown", False))

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5,
                               options="-c statement_timeout=10000 -c lock_timeout=5000")

    def initialize(self):
        with self.connect() as db:
            db.execute(Path(__file__).with_name("schema.sql").read_text())

    def check_schema(self):
        with self.connect() as db:
            for table in ("admission_seen", "admission_groups", "admission_counts", "admission_reports", "admission_outbox", "admission_budget", "admission_binding"):
                db.execute(f"SELECT 1 FROM {table} LIMIT 0")

    def lock(self, db):
        # Shared by intake, report scheduling and publish claims across replicas.
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (self.policy.cluster,))

    def now(self, explicit=None):
        if explicit is not None:  # In-process test clock; no HTTP clock override.
            return explicit
        with self.connect() as db:
            return db.execute("SELECT clock_timestamp() AS now").fetchone()["now"]

    def bind(self, db, now):
        day = self.policy.local_day(now)
        db.execute("INSERT INTO admission_binding VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                   (self.policy.cluster,self.policy.timezone_name,self.policy.triage_topic,day))
        binding = db.execute("SELECT * FROM admission_binding WHERE cluster=%s FOR UPDATE", (self.policy.cluster,)).fetchone()
        if binding["timezone_name"] != self.policy.timezone_name or binding["triage_topic"] != self.policy.triage_topic or day < binding["last_day"]:
            raise RuntimeError("publication binding changed or clock moved backwards")
        db.execute("UPDATE admission_binding SET last_day=%s WHERE cluster=%s", (day,self.policy.cluster))

    def validate(self, payload, now):
        if not isinstance(payload, dict) or payload.get("schema_version") != "observability.triage.v2":
            raise ValueError("unsupported signal contract")
        if payload.get("cluster") != self.policy.cluster or payload.get("namespace") not in self.policy.namespaces:
            raise ValueError("source scope rejected")
        if payload.get("signal_kind") not in ("event", "log") or payload.get("severity") not in SEVERITY:
            raise ValueError("invalid signal kind or severity")
        if payload.get("automation_allowed") is not False:
            raise ValueError("read-only signal required")
        observed = instant(payload.get("observed_timestamp", ""))
        if observed < now - timedelta(hours=24) or observed > now + timedelta(minutes=5):
            raise ValueError("stale or future observation")
        for key in ("reason", "pod", "delivery_key", "dedupe_key"):
            if not isinstance(payload.get(key), str) or not 1 <= len(payload[key]) <= 256:
                raise ValueError("missing or oversized identity")
        if not isinstance(payload.get("evidence"), dict):
            raise ValueError("missing bounded evidence")
        # Keep only the existing public envelope; never store raw OTLP extras.
        result = {k: v for k, v in payload.items() if k in FIELDS}
        evidence = payload["evidence"]
        result["evidence"] = {k: str(evidence.get(k, ""))[:1024]
                              for k in ("event_summary", "representative_log_lines")}
        # Defense in depth for common credential patterns. This is not a complete
        # secret detector; the upstream approved redaction remains mandatory.
        for k, value in result["evidence"].items():
            value = re.sub(r"(?i)(password|token|secret|api[_-]?key)\s*[=:]\s*[^\s,;]+", "[REDACTED]", value)
            result["evidence"][k] = re.sub(r"(?i)bearer\s+\S+", "[REDACTED]", value)
        if len(canonical(result).encode()) > 16384:
            raise ValueError("signal exceeds envelope bound")
        return result, observed

    def ingest(self, payload, now=None):
        now = self.now(now)
        payload, observed = self.validate(payload, now)
        owner_kind, owner_name, resolved = self.resolver(payload)
        group = identity(self.policy.cluster, payload["namespace"], owner_kind, owner_name, payload["reason"])
        # Stable for HTTP retries but distinct for new observations of the same
        # delivery_key (which is an incident key, NOT a unique observation ID).
        record = identity(payload)
        # Keep the v2 envelope but correlate downstream on actual stable owner.
        # This migration requires reconciling pre-cutover pod-keyed tickets.
        payload["dedupe_key"] = identity(self.policy.cluster, payload["namespace"], owner_kind, owner_name)
        bucket = observed.replace(minute=observed.minute // 5 * 5, second=0, microsecond=0)
        with self.connect() as db:
            self.lock(db)
            inserted = db.execute("INSERT INTO admission_seen VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING record_id",
                                  (self.policy.cluster, record, now)).fetchone()
            if not inserted:
                return {"accepted": True, "duplicate": True}
            existing = db.execute("SELECT 1 FROM admission_groups WHERE cluster=%s AND group_id=%s",
                                  (self.policy.cluster, group)).fetchone()
            if not existing:
                total = db.execute("SELECT count(*) AS n FROM admission_groups WHERE cluster=%s",
                                   (self.policy.cluster,)).fetchone()["n"]
                if total >= self.policy.max_groups:
                    raise RuntimeError("group capacity exceeded")
            db.execute("""INSERT INTO admission_groups VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(cluster,group_id) DO UPDATE SET
                last_seen=GREATEST(admission_groups.last_seen,excluded.last_seen),
                severity=CASE WHEN excluded.last_seen>=admission_groups.last_seen THEN excluded.severity ELSE admission_groups.severity END,
                payload=CASE WHEN excluded.last_seen>=admission_groups.last_seen THEN excluded.payload ELSE admission_groups.payload END""",
                (self.policy.cluster, group, payload["namespace"], owner_kind, owner_name, payload["reason"],
                 observed, observed, payload["severity"], Jsonb(payload), resolved))
            db.execute("""INSERT INTO admission_counts VALUES(%s,%s,%s,1)
                ON CONFLICT(cluster,group_id,bucket) DO UPDATE SET records=admission_counts.records+1""",
                (self.policy.cluster, group, bucket))
        return {"accepted": True, "duplicate": False, "identity_resolved": resolved}

    def enqueue(self, db, group, namespace, lane, payload, topic, now):
        if lane not in ("routine", "digest"):
            raise ValueError("no urgent or other publication bypass")
        if lane == "routine" and (namespace not in self.policy.namespaces or topic != self.policy.triage_topic):
            raise ValueError("routine publication scope rejected")
        if lane == "digest" and (namespace != "_cluster" or topic != self.policy.digest_topic or group != "daily-digest"):
            raise ValueError("digest publication scope rejected")
        day = self.policy.local_day(now)
        intent = identity(self.policy.cluster, str(day), namespace, lane, group)
        # No contract mutation: admission identity travels as a Kafka header.
        db.execute("""INSERT INTO admission_outbox(intent_id,cluster,local_day,namespace,lane,group_id,topic,payload,created_at,updated_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (intent, self.policy.cluster, day, namespace, lane, group, topic, Jsonb(payload), now, now))

    def report(self, now=None):
        now = self.now(now)
        if not self.policy.due(now):
            return None
        day = self.policy.local_day(now)
        with self.connect() as db:
            self.lock(db)
            if self.policy.mode == "enforce":
                self.bind(db, now)
            old = db.execute("SELECT body FROM admission_reports WHERE cluster=%s AND local_day=%s AND mode=%s",
                             (self.policy.cluster, day, self.policy.mode)).fetchone()
            if old:
                return old["body"]
            groups = db.execute("""SELECT g.*, sum(c.records)::bigint AS received_records
                FROM admission_groups g JOIN admission_counts c USING(cluster,group_id)
                WHERE g.cluster=%s AND c.bucket >= %s AND c.bucket <= %s
                GROUP BY g.cluster,g.group_id""", (self.policy.cluster, now - timedelta(hours=24), now)).fetchall()
            groups.sort(key=lambda g: (-SEVERITY[g["severity"]], -int(g["last_seen"] >= now-timedelta(hours=1)),
                                       -g["received_records"], g["group_id"]))
            used, selected, candidates = {}, [], []
            for g in groups:
                ns = g["namespace"]
                entry = {"id": g["group_id"], "namespace": ns, "owner_kind": g["owner_kind"],
                         "owner_name": g["owner_name"], "identity_resolved": g["identity_resolved"],
                         "reason": g["reason"], "severity": g["severity"], "received_records": g["received_records"],
                         "last_seen": g["last_seen"].isoformat(), "sample": g["payload"]["evidence"],
                         "selected": False}
                if used.get(ns, 0) < self.policy.overrides.get(ns, self.policy.limit):
                    used[ns] = used.get(ns, 0) + 1
                    entry["selected"] = True
                    selected.append(entry)
                    if self.policy.mode == "enforce":
                        self.enqueue(db, g["group_id"], ns, "routine", g["payload"], self.policy.triage_topic, now)
                candidates.append(entry)
            # Cluster candidates are chosen BEFORE namespace trimming. They are
            # hypotheses, not correlated root causes or a health verdict.
            document = {"schema_version": "namespace-triage.digest.v1", "cluster": self.policy.cluster,
                        "local_day": str(day), "timezone": self.policy.timezone_name,
                        "generated_at": now.isoformat(), "mode": self.policy.mode,
                        "candidate_total": len(candidates), "received_records": sum(g["received_records"] for g in groups),
                        "namespace_selected": {n: used.get(n, 0) for n in self.policy.namespaces},
                        "selected_total": len(selected), "deferred_total": sum(not c["selected"] for c in candidates),
                        "candidates": candidates[:10], "candidates_truncated": len(candidates)>10,
                        "top_three_candidates": [c["id"] for c in candidates[:3]],
                        "coverage_complete": False,
                        "limitations": ["Only allow-listed event/log signal envelopes are collected.",
                            "Counts are unique received envelopes, not Kubernetes Event occurrence deltas.",
                            "Metric alerts, current workload state and SLO impact are not collected by this gate.",
                            "Silence is not recovery; priority is provisional until read-only investigation."]}
            # Bound by trimming samples first, then examples; totals remain intact.
            while len(canonical(document).encode()) > 32768 and document["candidates"]:
                document["candidates"].pop()
                document["candidates_truncated"] = True
            document["top_three_candidates"] = [c["id"] for c in document["candidates"][:3]]
            db.execute("INSERT INTO admission_reports VALUES(%s,%s,%s,%s,%s)",
                       (self.policy.cluster, day, self.policy.mode, Jsonb(document), now))
            if self.policy.mode == "enforce" and self.policy.digest_topic:
                self.enqueue(db, "daily-digest", "_cluster", "digest", document, self.policy.digest_topic, now)
            return document

    def publish_one(self, producer, now=None):
        now = self.now(now)
        if self.policy.mode != "enforce":
            return False
        with self.connect() as db:
            self.lock(db)
            self.bind(db, now)
            row = db.execute("""SELECT * FROM admission_outbox WHERE cluster=%s AND status='pending'
                ORDER BY created_at,intent_id LIMIT 1 FOR UPDATE""",
                (self.policy.cluster,)).fetchone()
            if not row:
                return False
            # Never drain old reports, legacy urgent records or changed topics.
            expired = row["local_day"] != self.policy.local_day(now) or row["created_at"] < now-timedelta(hours=1)
            expired |= row["lane"] not in ("routine", "digest")
            expired |= row["lane"] == "routine" and (row["namespace"] not in self.policy.namespaces or row["topic"] != self.policy.triage_topic)
            expired |= row["lane"] == "digest" and (row["namespace"] != "_cluster" or row["topic"] != self.policy.digest_topic)
            # Leave a full minute for transaction initialization, audit and send.
            local = now.astimezone(ZoneInfo(self.policy.timezone_name))
            expired |= local.hour == 23 and local.minute == 59
            if not expired:
                ceiling = 1 if row["lane"] == "digest" else self.policy.overrides.get(row["namespace"], self.policy.limit)
                budget = db.execute("""INSERT INTO admission_budget VALUES(%s,%s,%s,%s,1)
                    ON CONFLICT(cluster,local_day,namespace) DO UPDATE SET
                      used=admission_budget.used+1
                    WHERE admission_budget.used < LEAST(admission_budget.ceiling,excluded.ceiling)
                    RETURNING used""",(row["cluster"],row["local_day"],row["namespace"],ceiling)).fetchone()
                expired = not budget
            db.execute("UPDATE admission_outbox SET status=%s,updated_at=%s WHERE intent_id=%s",
                       ("expired" if expired else "sending", now, row["intent_id"]))
        if expired:
            return True
        # Serialize broker reconciliation AND sending across all gate replicas.
        # Claimed slots already committed above survive a process failure.
        with self.connect() as db:
            self.lock(db)
            try:
                verdict = producer.check(row, self.policy, now, ceiling)
                if verdict == "already-sent":
                    status = "sent"
                elif verdict == "full":
                    status = "expired"
                elif verdict == "available":
                    producer.send(row["topic"], row["payload"].get("dedupe_key", row["intent_id"]),
                                  row["payload"], row["intent_id"], row["cluster"],row["namespace"],str(row["local_day"]))
                    status = "sent"
                else:
                    raise RuntimeError("invalid broker reconciliation")
            except Exception:
                LOG.error("Kafka outcome or history unknown; publication fails closed")
                status = "unknown"
            db.execute("UPDATE admission_outbox SET status=%s,updated_at=%s WHERE intent_id=%s",
                       (status, now, row["intent_id"]))
        return True

    def prune(self, now=None):
        now = self.now(now)
        with self.connect() as db:
            self.lock(db)
            for table, column, days in (("admission_seen", "received_at", 2), ("admission_counts", "bucket", 8),
                                        ("admission_groups", "last_seen", 8), ("admission_reports", "created_at", 30)):
                db.execute(f"DELETE FROM {table} WHERE cluster=%s AND {column}<%s",
                           (self.policy.cluster, now-timedelta(days=days)))
            # Retain ambiguous outcomes for 30 days without retrying. The
            # monotonic binding prevents refilling any expired historical day.
            db.execute("DELETE FROM admission_outbox WHERE cluster=%s AND created_at<%s",
                       (self.policy.cluster, now-timedelta(days=30)))
            db.execute("DELETE FROM admission_budget WHERE cluster=%s AND local_day<%s",
                       (self.policy.cluster, self.policy.local_day(now)-timedelta(days=30)))


class KafkaPublisher:
    def __init__(self, allow_plaintext=False, expected_topic_ids=None):
        from confluent_kafka import Producer
        config = json.loads(os.environ.get("KAFKA_SECURITY_CONFIG", "{}"))
        if not allow_plaintext and config.get("security.protocol") not in ("SSL", "SASL_SSL"):
            raise ValueError("Kafka TLS configuration required")
        config.update({"bootstrap.servers": os.environ["CONFLUENT_BOOTSTRAP"], "enable.idempotence": True,
                       "acks": "all", "message.timeout.ms": 10000, "queue.buffering.max.messages": 10})
        self.config = dict(config)
        self.expected_topic_ids = expected_topic_ids if expected_topic_ids is not None else json.loads(os.environ.get("KAFKA_TOPIC_IDS", "{}"))
        self.client = Producer(config)

    def check(self, row, policy, now, ceiling):
        from confluent_kafka import Consumer, Producer, KafkaError, TopicCollection, TopicPartition
        from confluent_kafka.admin import AdminClient, ConfigResource, ResourceType
        topic = row["topic"]
        expected = self.expected_topic_ids.get(topic)
        if not expected:
            raise RuntimeError("externally pinned Kafka topic ID required")
        security = {k:v for k,v in self.config.items() if k=="bootstrap.servers" or k.startswith(("security.","sasl.","ssl."))}
        admin = AdminClient(security)
        description = admin.describe_topics(TopicCollection([topic]), request_timeout=3)[topic].result(4)
        if str(description.topic_id) != expected:
            raise RuntimeError("Kafka topic was replaced")
        resource = ConfigResource(ResourceType.TOPIC,topic)
        configs = admin.describe_configs([resource],request_timeout=3)[resource].result(4)
        if configs["cleanup.policy"].value != "delete" or int(configs["retention.bytes"].value) != -1 or \
                (int(configs["retention.ms"].value) != -1 and int(configs["retention.ms"].value)<172800000):
            raise RuntimeError("Kafka history retention cannot prove remaining allowance")
        # Fence earlier publishers before auditing committed history. This also
        # resolves an ambiguous transaction after a database restore or crash.
        self.client = Producer({**self.config,"transactional.id":"admission-"+identity(row["cluster"])})
        self.client.init_transactions(5)
        consumer = Consumer({**security,"isolation.level":"read_committed","group.id":"admission-audit-"+identity(row["intent_id"],time.time_ns()),
            "enable.auto.commit":False,"allow.auto.create.topics":False,"enable.partition.eof":True})
        targets, start_offsets, heads = {}, {}, {}
        count, already, scanned = 0, False, 0
        deadline = time.monotonic()+5
        try:
            assignment=[]
            for part in description.partitions:
                low,high=consumer.get_watermark_offsets(TopicPartition(topic,part.id),timeout=2,cached=False)
                targets[part.id]=high; start_offsets[part.id]=low
                assignment.append(TopicPartition(topic,part.id,low))
            consumer.assign(assignment)
            positions=dict(start_offsets)
            while any(positions[p]<high for p,high in targets.items()):
                if time.monotonic()>deadline or scanned>=10000:
                    raise RuntimeError("bounded Kafka audit incomplete")
                message=consumer.poll(.2)
                if message is None: continue
                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        positions[message.partition()] = message.offset()
                        continue
                    raise RuntimeError("Kafka audit failed")
                positions[message.partition()]=message.offset()+1
                scanned+=1
                timestamp=message.timestamp()[1]
                heads.setdefault(message.partition(),timestamp)
                value=json.loads(message.value())
                headers={k:(v.decode() if isinstance(v,bytes) else v) for k,v in (message.headers() or [])}
                cluster=headers.get("admission-cluster",value.get("cluster"))
                namespace=headers.get("admission-namespace",value.get("namespace"))
                day=headers.get("admission-local-day")
                if day is None:
                    if timestamp<0: raise RuntimeError("record day unavailable")
                    day=str(policy.local_day(datetime.fromtimestamp(timestamp/1000,UTC)))
                if cluster==row["cluster"] and namespace==row["namespace"] and day==str(row["local_day"]):
                    count+=1
                    already |= headers.get("admission-intent-id")==row["intent_id"]
            midnight=datetime.combine(policy.local_day(now),datetime.min.time(),ZoneInfo(policy.timezone_name)).timestamp()*1000
            for part,low in start_offsets.items():
                if low>0 and (part not in heads or heads[part]>=midnight):
                    raise RuntimeError("Kafka current-day history was truncated")
            if already: return "already-sent"
            return "full" if count>=ceiling else "available"
        finally:
            consumer.close()

    def send(self, topic, key, payload, intent, cluster, namespace, day):
        outcomes = []
        self.client.begin_transaction()
        self.client.produce(topic, key=key, value=canonical(payload).encode(),
                            headers={"admission-intent-id": intent,"admission-cluster":cluster,
                                     "admission-namespace":namespace,"admission-local-day":day},
                            on_delivery=lambda error, message: outcomes.append(error))
        remaining = self.client.flush(12)
        if remaining or not outcomes or outcomes[0] is not None:
            raise RuntimeError("Kafka delivery unconfirmed")
        self.client.commit_transaction(5)


def handler_for(gate, auth_key):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log evidence, paths or authorization headers.

        def respond(self, status, body):
            data = canonical(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authenticated(self):
            return hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + auth_key)

        def do_GET(self):
            if self.path == "/health":
                try:
                    with gate.connect() as db:
                        db.execute("SELECT 1")
                    return self.respond(200, {"ready": True})
                except Exception:
                    return self.respond(503, {"ready": False})
            if not self.authenticated():
                return self.respond(401, {"error": "unauthorized"})
            if self.path == "/metrics":
                try:
                    with gate.connect() as db:
                        rows = db.execute("SELECT lane,status,count(*) AS n FROM admission_outbox WHERE cluster=%s GROUP BY lane,status",
                                          (gate.policy.cluster,)).fetchall()
                    lines = ["# TYPE admission_outbox_intents gauge"]
                    lines += ['admission_outbox_intents{lane="%s",status="%s"} %s' % (r["lane"],r["status"],r["n"]) for r in rows]
                    data = ("\n".join(lines)+"\n").encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception:
                    return self.respond(503, {"error": "state unavailable"})
            if self.path == "/report":
                try:
                    with gate.connect() as db:
                        row = db.execute("SELECT body FROM admission_reports WHERE cluster=%s AND mode=%s ORDER BY local_day DESC LIMIT 1",
                                         (gate.policy.cluster, gate.policy.mode)).fetchone()
                    return self.respond(200 if row else 404, row["body"] if row else {"error": "no report"})
                except Exception:
                    return self.respond(503, {"error": "state unavailable"})
            return self.respond(404, {"error": "not found"})

        def do_POST(self):
            if not self.authenticated():
                return self.respond(401, {"error": "unauthorized"})
            if self.path != "/signals":
                return self.respond(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32768:
                    return self.respond(413, {"error": "invalid body size"})
                self.connection.settimeout(5)
                payload = json.loads(self.rfile.read(length))
                result = gate.ingest(payload)
                return self.respond(200, result)  # Only after database commit.
            except (ValueError, TypeError):
                return self.respond(400, {"error": "signal rejected"})
            except Exception:
                return self.respond(503, {"error": "state or intake unavailable"})
    return Handler


def main():
    logging.basicConfig(level=logging.INFO)
    settings = json.loads(Path(os.environ.get("POLICY_FILE", "/etc/admission/policy.json")).read_text())
    settings["namespaces"] = tuple(settings["namespaces"])
    policy = Policy(**settings)
    auth_key = os.environ["ADMISSION_AUTH_KEY"]
    if len(auth_key) < 32:
        raise ValueError("auth key must have at least 32 characters")
    gate = Gate(os.environ["DATABASE_URL"], policy, OwnerResolver())
    gate.check_schema()  # Migrations use a separately authorized database owner.
    producer = KafkaPublisher() if policy.mode == "enforce" else None

    def run():
        while True:
            try:
                gate.prune()
                gate.report()
                if producer:
                    for _ in range(100):
                        if not gate.publish_one(producer):
                            break
            except Exception:
                LOG.error("admission scheduler failed; routine publication paused")
            time.sleep(10)

    threading.Thread(target=run, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8080), handler_for(gate, auth_key)).serve_forever()


if __name__ == "__main__":
    main()
