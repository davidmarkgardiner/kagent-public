"""Disposable broker proof. Never run against a workplace topic/database."""
import os
import time
from datetime import datetime, timezone

from confluent_kafka import Consumer
from gate import Gate, KafkaPublisher, Policy
from test_gate import signal

now = datetime.now(timezone.utc)
gate = Gate(os.environ["TEST_DATABASE_URL"], Policy(
    "test-cluster", ("apps",), mode="enforce", triage_topic="admission-proof",
    report_hour=0, limit=2), lambda p: ("Deployment", p["pod"], True))
gate.initialize()
with gate.connect() as db:
    db.execute("TRUNCATE admission_seen,admission_groups,admission_counts,admission_reports,admission_outbox,admission_budget,admission_binding")
for n in range(40):
    gate.ingest(signal(n, observed=now), now)
report = gate.report(now)
from confluent_kafka import TopicCollection
from confluent_kafka.admin import AdminClient, NewTopic
admin = AdminClient({"bootstrap.servers":os.environ["CONFLUENT_BOOTSTRAP"]})
admin.create_topics([NewTopic("admission-proof", 1, 1, config={"cleanup.policy":"delete","retention.ms":"172800000","retention.bytes":"-1"})])["admission-proof"].result(10)
pin = str(admin.describe_topics(TopicCollection(["admission-proof"]))["admission-proof"].result(10).topic_id)
publisher = KafkaPublisher(allow_plaintext=True, expected_topic_ids={"admission-proof":pin})  # Disposable local broker only.
while gate.publish_one(publisher, now):
    pass
consumer = Consumer({"bootstrap.servers": os.environ["CONFLUENT_BOOTSTRAP"],
                     "group.id": "admission-proof-"+str(time.time_ns()),
                     "auto.offset.reset": "earliest", "enable.auto.commit": False, "isolation.level":"read_committed"})
consumer.subscribe(["admission-proof"])
messages = []
deadline = time.monotonic()+20
try:
    while time.monotonic()<deadline:
        message = consumer.poll(1)
        if message and not message.error():
            messages.append(message)
finally:
    consumer.close()
assert len(messages) == 2, len(messages)
assert len({dict(m.headers())["admission-intent-id"] for m in messages}) == 2
assert report["received_records"] == 40 and report["deferred_total"] == 38
assert not gate.publish_one(publisher, now)
print("KAFKA_PROOF_PASS: 40 stored signals, 2 produced AND consumed, 38 deferred; replay sends zero.")
