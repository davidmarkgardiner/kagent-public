"""Isolated Docker test intake; synthetic identity resolution only."""
import os
from http.server import ThreadingHTTPServer
from gate import Gate, Policy, handler_for

gate = Gate(os.environ["TEST_DATABASE_URL"], Policy("test-cluster", ("apps",)),
            lambda p: ("Deployment", p["pod"], True))
gate.initialize()
with gate.connect() as db:
    db.execute("TRUNCATE admission_seen,admission_groups,admission_counts,admission_reports,admission_outbox")
ThreadingHTTPServer(("0.0.0.0", 8080), handler_for(gate, os.environ["ADMISSION_AUTH_KEY"])).serve_forever()
