#!/usr/bin/env python3
"""Durable, deterministic finding lifecycle for the smart-triage POC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "smart-triage-finding/v1"
SEVERITY_RANK = {"info": 1, "warning": 2, "critical": 3}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_REASON = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SAFE_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SENSITIVE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._~+/=-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:password|passwd|client_secret|access_token|refresh_token)\s*[:=]\s*\S+)"
)


class ContractError(ValueError):
    """Finding does not satisfy the public contract."""


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"invalid RFC3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _require_keys(value: dict[str, Any], required: set[str], allowed: set[str], path: str) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        raise ContractError(f"{path} missing required fields: {', '.join(missing)}")
    if extra:
        raise ContractError(f"{path} contains unsupported fields: {', '.join(extra)}")


def _bounded_string(value: Any, path: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ContractError(f"{path} must be a string with length {minimum}..{maximum}")
    if SENSITIVE.search(value):
        raise ContractError(f"{path} contains credential-like material")
    return value


def validate_finding(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractError("finding must be a JSON object")
    top = {
        "schemaVersion", "runId", "observedAt", "observationStatus", "target",
        "resource", "finding", "evidence", "provenance", "recommendedActions",
    }
    _require_keys(payload, top, top, "finding")
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ContractError(f"schemaVersion must be {SCHEMA_VERSION!r}")
    run_id = _bounded_string(payload["runId"], "runId", 1, 128)
    if not SAFE_ID.fullmatch(run_id):
        raise ContractError("runId contains unsupported characters")
    parse_time(payload["observedAt"])
    if payload["observationStatus"] not in {"firing", "resolved"}:
        raise ContractError("observationStatus must be firing or resolved")

    target = payload["target"]
    if not isinstance(target, dict):
        raise ContractError("target must be an object")
    target_keys = {"subscriptionScope", "cluster", "environment", "namespace"}
    _require_keys(target, target_keys, target_keys, "target")
    _bounded_string(target["subscriptionScope"], "target.subscriptionScope", 1, 128)
    _bounded_string(target["cluster"], "target.cluster", 1, 253)
    _bounded_string(target["environment"], "target.environment", 1, 64)
    _bounded_string(target["namespace"], "target.namespace", 1, 253)

    resource = payload["resource"]
    if not isinstance(resource, dict):
        raise ContractError("resource must be an object")
    resource_keys = {"kind", "stableWorkload", "observedResource"}
    _require_keys(resource, resource_keys, resource_keys, "resource")
    _bounded_string(resource["kind"], "resource.kind", 1, 64)
    _bounded_string(resource["stableWorkload"], "resource.stableWorkload", 0, 253)
    _bounded_string(resource["observedResource"], "resource.observedResource", 0, 253)

    finding = payload["finding"]
    if not isinstance(finding, dict):
        raise ContractError("finding.finding must be an object")
    finding_keys = {"domain", "reason", "severity", "confidence", "summary", "identityStatus"}
    _require_keys(finding, finding_keys, finding_keys, "finding.finding")
    domain = _bounded_string(finding["domain"], "finding.domain", 1, 64)
    reason = _bounded_string(finding["reason"], "finding.reason", 1, 96)
    if not SAFE_DOMAIN.fullmatch(domain):
        raise ContractError("finding.domain must be a lowercase machine token")
    if not SAFE_REASON.fullmatch(reason):
        raise ContractError("finding.reason must be a machine token")
    if finding["severity"] not in SEVERITY_RANK:
        raise ContractError("finding.severity must be info, warning or critical")
    if finding["confidence"] not in {"low", "medium", "high"}:
        raise ContractError("finding.confidence must be low, medium or high")
    _bounded_string(finding["summary"], "finding.summary", 1, 1000)
    if finding["identityStatus"] not in {"canonical", "provisional"}:
        raise ContractError("finding.identityStatus must be canonical or provisional")
    if finding["identityStatus"] == "canonical" and not resource["stableWorkload"].strip():
        raise ContractError("canonical findings require resource.stableWorkload")

    evidence = payload["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 20:
        raise ContractError("evidence must be an array with at most 20 items")
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ContractError(f"evidence[{index}] must be an object")
        keys = {"source", "reference", "observedAt"}
        _require_keys(item, keys, keys, f"evidence[{index}]")
        _bounded_string(item["source"], f"evidence[{index}].source", 1, 64)
        _bounded_string(item["reference"], f"evidence[{index}].reference", 1, 500)
        parse_time(item["observedAt"])

    provenance = payload["provenance"]
    if not isinstance(provenance, dict):
        raise ContractError("provenance must be an object")
    provenance_keys = {"agent", "tools"}
    _require_keys(provenance, provenance_keys, provenance_keys, "provenance")
    _bounded_string(provenance["agent"], "provenance.agent", 1, 128)
    if not isinstance(provenance["tools"], list) or len(provenance["tools"]) > 20:
        raise ContractError("provenance.tools must be an array with at most 20 items")
    for index, tool in enumerate(provenance["tools"]):
        _bounded_string(tool, f"provenance.tools[{index}]", 1, 128)

    actions = payload["recommendedActions"]
    if not isinstance(actions, list) or len(actions) > 10:
        raise ContractError("recommendedActions must be an array with at most 10 items")
    for index, action in enumerate(actions):
        _bounded_string(action, f"recommendedActions[{index}]", 1, 500)
    return payload


def identity_key(payload: dict[str, Any]) -> str:
    target = payload["target"]
    resource = payload["resource"]
    finding = payload["finding"]
    parts = (
        target["subscriptionScope"], target["cluster"], target["namespace"],
        resource["stableWorkload"], finding["domain"], finding["reason"],
    )
    return "/".join(part.strip().lower() for part in parts)


def fingerprint(payload: dict[str, Any]) -> str:
    key = identity_key(payload)
    return "stf-v1-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


class LifecycleStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self._lock = threading.RLock()
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS findings (
                  fingerprint TEXT PRIMARY KEY,
                  identity_key TEXT NOT NULL UNIQUE,
                  subscription_scope TEXT NOT NULL,
                  cluster TEXT NOT NULL,
                  namespace TEXT NOT NULL,
                  stable_workload TEXT NOT NULL,
                  domain TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  severity TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  first_seen TEXT NOT NULL,
                  last_seen TEXT NOT NULL,
                  times_seen INTEGER NOT NULL,
                  recurrence_count INTEGER NOT NULL DEFAULT 0,
                  resolved_at TEXT,
                  ack_until TEXT,
                  canonical_issue_url TEXT,
                  latest_run_id TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS findings_scope
                  ON findings(subscription_scope, cluster, domain, resolved_at);
                CREATE TABLE IF NOT EXISTS evaluations (
                  run_id TEXT NOT NULL,
                  fingerprint TEXT NOT NULL,
                  payload_hash TEXT NOT NULL,
                  decision_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (run_id, fingerprint)
                );
                CREATE TABLE IF NOT EXISTS acknowledgements (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fingerprint TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  ack_until TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS issue_links (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fingerprint TEXT NOT NULL,
                  issue_url TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                """
            )

    def health(self) -> dict[str, Any]:
        with self._connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        return {"status": "ok", "stateBackend": "sqlite-pvc", "durableState": True, "findingCount": count}

    @staticmethod
    def _decision(status: str, fp: str, payload: dict[str, Any], times_seen: int = 0,
                  previous_severity: str | None = None, notify: bool = False,
                  auto_ticket: bool = False, idempotent: bool = False,
                  ticket_action: str = "NONE") -> dict[str, Any]:
        return {
            "schemaVersion": "smart-triage-lifecycle-decision/v1",
            "runId": payload["runId"],
            "fingerprint": fp,
            "status": status,
            "severity": payload["finding"]["severity"],
            "previousSeverity": previous_severity,
            "timesSeen": times_seen,
            "notify": notify,
            "autoTicketAllowed": auto_ticket,
            "ticketAction": ticket_action,
            "idempotentReplay": idempotent,
        }

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = validate_finding(payload)
        fp = fingerprint(payload)
        if payload["finding"]["identityStatus"] == "provisional":
            return self._decision("PROVISIONAL", fp, payload, notify=True, auto_ticket=False)

        payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        observed = parse_time(payload["observedAt"]).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            prior_eval = connection.execute(
                "SELECT payload_hash, decision_json FROM evaluations WHERE run_id=? AND fingerprint=?",
                (payload["runId"], fp),
            ).fetchone()
            if prior_eval:
                if prior_eval["payload_hash"] != payload_hash:
                    raise ContractError("runId was already used with a different payload")
                decision = json.loads(prior_eval["decision_json"])
                decision["idempotentReplay"] = True
                decision["notify"] = False
                decision["autoTicketAllowed"] = False
                decision["ticketAction"] = "NONE"
                return decision

            row = connection.execute("SELECT * FROM findings WHERE fingerprint=?", (fp,)).fetchone()
            stale = bool(row and parse_time(observed) < parse_time(row["last_seen"]))
            if stale:
                decision = self._decision(
                    "STALE", fp, payload, row["times_seen"], row["severity"],
                    notify=False, auto_ticket=False,
                )
            elif payload["observationStatus"] == "resolved":
                if row is None:
                    decision = self._decision("RESOLUTION_UNKNOWN", fp, payload)
                else:
                    connection.execute(
                        "UPDATE findings SET resolved_at=?, last_seen=?, latest_run_id=?, updated_at=? WHERE fingerprint=?",
                        (observed, observed, payload["runId"], now, fp),
                    )
                    decision = self._decision(
                        "RESOLVED", fp, payload, row["times_seen"], row["severity"], notify=True,
                        auto_ticket=bool(row["canonical_issue_url"]),
                        ticket_action="UPDATE" if row["canonical_issue_url"] else "NONE",
                    )
            elif row is None:
                finding = payload["finding"]
                target = payload["target"]
                resource = payload["resource"]
                connection.execute(
                    """INSERT INTO findings (
                      fingerprint, identity_key, subscription_scope, cluster, namespace,
                      stable_workload, domain, reason, severity, summary, first_seen,
                      last_seen, times_seen, recurrence_count, resolved_at, ack_until,
                      canonical_issue_url, latest_run_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, NULL, NULL, NULL, ?, ?)""",
                    (
                        fp, identity_key(payload), target["subscriptionScope"], target["cluster"],
                        target["namespace"], resource["stableWorkload"], finding["domain"],
                        finding["reason"], finding["severity"], finding["summary"], observed,
                        observed, payload["runId"], now,
                    ),
                )
                decision = self._decision(
                    "NEW", fp, payload, 1, notify=True, auto_ticket=True,
                    ticket_action="CREATE",
                )
            else:
                acked = bool(row["ack_until"] and parse_time(row["ack_until"]) > datetime.now(timezone.utc))
                recurrence = row["resolved_at"] is not None
                escalated = SEVERITY_RANK[payload["finding"]["severity"]] > SEVERITY_RANK[row["severity"]]
                times_seen = row["times_seen"] + 1
                recurrence_count = row["recurrence_count"] + (1 if recurrence else 0)
                if acked:
                    status, notify, ticket_action = "ACKNOWLEDGED", False, "NONE"
                elif recurrence:
                    status, notify = "RECURRENT", True
                    ticket_action = "UPDATE" if row["canonical_issue_url"] else "CREATE"
                elif escalated:
                    status, notify = "ESCALATED", True
                    ticket_action = "UPDATE" if row["canonical_issue_url"] else "CREATE"
                else:
                    status, notify, ticket_action = "ONGOING", False, "NONE"
                connection.execute(
                    """UPDATE findings SET severity=?, summary=?, last_seen=?, times_seen=?,
                       recurrence_count=?, resolved_at=NULL, latest_run_id=?, updated_at=?
                       WHERE fingerprint=?""",
                    (
                        payload["finding"]["severity"], payload["finding"]["summary"], observed,
                        times_seen, recurrence_count, payload["runId"], now, fp,
                    ),
                )
                decision = self._decision(
                    status, fp, payload, times_seen, row["severity"], notify,
                    auto_ticket=ticket_action != "NONE", ticket_action=ticket_action,
                )

            connection.execute(
                "INSERT INTO evaluations(run_id, fingerprint, payload_hash, decision_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload["runId"], fp, payload_hash, canonical_json(decision), now),
            )
            return decision

    def acknowledge(self, request: dict[str, Any]) -> dict[str, Any]:
        allowed = {"fingerprint", "actor", "ackUntil"}
        _require_keys(request, allowed, allowed, "acknowledgement")
        fp = _bounded_string(request["fingerprint"], "fingerprint", 1, 64)
        actor = _bounded_string(request["actor"], "actor", 1, 128)
        ack_until = parse_time(request["ackUntil"])
        if ack_until <= datetime.now(timezone.utc):
            raise ContractError("ackUntil must be in the future")
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT fingerprint FROM findings WHERE fingerprint=?", (fp,)).fetchone()
            if not row:
                raise ContractError("cannot acknowledge an unknown fingerprint")
            now = datetime.now(timezone.utc).isoformat()
            connection.execute("UPDATE findings SET ack_until=?, updated_at=? WHERE fingerprint=?", (ack_until.isoformat(), now, fp))
            connection.execute(
                "INSERT INTO acknowledgements(fingerprint, actor, ack_until, created_at) VALUES (?, ?, ?, ?)",
                (fp, actor, ack_until.isoformat(), now),
            )
        return {"fingerprint": fp, "status": "ACKNOWLEDGED", "ackUntil": ack_until.isoformat(), "actor": actor}

    def link_issue(self, request: dict[str, Any]) -> dict[str, Any]:
        allowed = {"fingerprint", "issueUrl", "actor"}
        _require_keys(request, allowed, allowed, "issue link")
        fp = _bounded_string(request["fingerprint"], "fingerprint", 1, 64)
        issue_url = _bounded_string(request["issueUrl"], "issueUrl", 1, 1000)
        actor = _bounded_string(request["actor"], "actor", 1, 128)
        parsed = urlparse(issue_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ContractError("issueUrl must be an HTTPS URL without embedded credentials")
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT fingerprint FROM findings WHERE fingerprint=?", (fp,)).fetchone()
            if not row:
                raise ContractError("cannot link an issue to an unknown fingerprint")
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE findings SET canonical_issue_url=?, updated_at=? WHERE fingerprint=?",
                (issue_url, now, fp),
            )
            connection.execute(
                "INSERT INTO issue_links(fingerprint, issue_url, actor, created_at) VALUES (?, ?, ?, ?)",
                (fp, issue_url, actor, now),
            )
        return {"fingerprint": fp, "status": "LINKED", "issueUrl": issue_url, "actor": actor}

    def snapshot(self, request: dict[str, Any]) -> dict[str, Any]:
        required = {"reportId", "observedAt", "subscriptionScope", "cluster", "domains", "findings", "completeSnapshot"}
        _require_keys(request, required, required, "snapshot")
        if request["completeSnapshot"] is not True:
            raise ContractError("snapshot resolution requires completeSnapshot=true")
        report_id = _bounded_string(request["reportId"], "reportId", 1, 128)
        observed_at = parse_time(request["observedAt"]).isoformat()
        subscription_scope = _bounded_string(request["subscriptionScope"], "subscriptionScope", 1, 128)
        cluster = _bounded_string(request["cluster"], "cluster", 1, 253)
        domains = request["domains"]
        if not isinstance(domains, list) or not domains:
            raise ContractError("domains must be a non-empty array")
        for domain in domains:
            if not isinstance(domain, str) or not SAFE_DOMAIN.fullmatch(domain):
                raise ContractError("snapshot domains must be lowercase machine tokens")
        findings = request["findings"]
        if not isinstance(findings, list) or len(findings) > 100:
            raise ContractError("findings must be an array with at most 100 items")

        decisions = []
        active = set()
        for index, item in enumerate(findings):
            if item.get("target", {}).get("subscriptionScope") != subscription_scope or item.get("target", {}).get("cluster") != cluster:
                raise ContractError(f"findings[{index}] is outside the declared snapshot scope")
            if item.get("finding", {}).get("domain") not in domains:
                raise ContractError(f"findings[{index}] is outside the declared snapshot domains")
            if item.get("observationStatus") != "firing":
                raise ContractError("snapshot findings must use observationStatus=firing")
            decision = self.evaluate(item)
            decisions.append(decision)
            if item["finding"]["identityStatus"] == "canonical":
                active.add(decision["fingerprint"])

        placeholders = ",".join("?" for _ in domains)
        query = (
            "SELECT * FROM findings WHERE subscription_scope=? AND cluster=? "
            f"AND domain IN ({placeholders}) AND resolved_at IS NULL"
        )
        resolved = []
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, (subscription_scope, cluster, *domains)).fetchall()
            for row in rows:
                if row["fingerprint"] in active:
                    continue
                connection.execute(
                    "UPDATE findings SET resolved_at=?, last_seen=?, latest_run_id=?, updated_at=? WHERE fingerprint=?",
                    (observed_at, observed_at, report_id, now, row["fingerprint"]),
                )
                resolved.append({
                    "fingerprint": row["fingerprint"], "status": "RESOLVED",
                    "previousSeverity": row["severity"], "timesSeen": row["times_seen"],
                    "notify": row["ack_until"] is None,
                })
        return {"reportId": report_id, "decisions": decisions, "resolved": resolved}

    def list_findings(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT fingerprint, subscription_scope, cluster, namespace,
                   stable_workload, domain, reason, severity, first_seen, last_seen,
                   times_seen, recurrence_count, resolved_at, ack_until,
                   canonical_issue_url, latest_run_id FROM findings ORDER BY updated_at DESC"""
            ).fetchall()
        return {"findings": [dict(row) for row in rows]}


class Handler(BaseHTTPRequestHandler):
    store: LifecycleStore

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            if self.path == "/healthz":
                self._send(200, self.store.health())
            elif self.path == "/v1/findings":
                self._send(200, self.store.list_findings())
            else:
                self._send(404, {"error": "not found"})
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._send(500, {"error": str(exc), "marker": "STATE_UNAVAILABLE"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 262144:
                raise ContractError("request body exceeds 256 KiB")
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if self.path == "/v1/findings/evaluate":
                result = self.store.evaluate(payload)
            elif self.path == "/v1/findings/acknowledge":
                result = self.store.acknowledge(payload)
            elif self.path == "/v1/findings/link-issue":
                result = self.store.link_issue(payload)
            elif self.path == "/v1/reports/evaluate":
                result = self.store.snapshot(payload)
            else:
                self._send(404, {"error": "not found"})
                return
            self._send(200, result)
        except (ContractError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc), "marker": "FINDING_CONTRACT_REJECTED"})
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            print(f"lifecycle error: {exc}", file=sys.stderr, flush=True)
            self._send(500, {"error": str(exc), "marker": "STATE_UNAVAILABLE"})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(fmt % args, flush=True)


def serve(database_path: str, host: str, port: int) -> None:
    Handler.store = LifecycleStore(database_path)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"smart-triage finding lifecycle listening on {host}:{port}", flush=True)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=os.environ.get("DATABASE_PATH", "/data/findings.db"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--validate", help="Validate one finding JSON file")
    arguments = parser.parse_args()
    if arguments.validate:
        payload = json.loads(Path(arguments.validate).read_text(encoding="utf-8"))
        validate_finding(payload)
        print(canonical_json({"status": "valid", "fingerprint": fingerprint(payload)}))
        return 0
    serve(arguments.database, arguments.host, arguments.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
