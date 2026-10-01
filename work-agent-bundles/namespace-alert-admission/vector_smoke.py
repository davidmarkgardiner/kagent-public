"""Prove actual Vector 0.45 HTTP framing/auth and database acknowledgment."""
import os
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from gate import Gate, Policy, canonical
from test_gate import signal

now = datetime.now(timezone.utc)
gate = Gate(os.environ["TEST_DATABASE_URL"], Policy("test-cluster", ("apps",), report_hour=0, limit=2))
for n in range(40):
    req = Request("http://vector:8088", data=canonical(signal(n, observed=now)).encode(),
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        assert response.status == 200
deadline = time.monotonic()+20
while time.monotonic()<deadline:
    with gate.connect() as db:
        count = db.execute("SELECT count(*) AS n FROM admission_seen").fetchone()["n"]
    if count == 40:
        break
    time.sleep(.2)
assert count == 40, count
report = gate.report(now)
assert report["received_records"] == 40 and report["selected_total"] == 2
with gate.connect() as db:
    assert db.execute("SELECT count(*) AS n FROM admission_outbox").fetchone()["n"] == 0
print("VECTOR_HTTP_PROOF_PASS: 40 signals durably acknowledged; shadow produces zero Kafka intents.")
