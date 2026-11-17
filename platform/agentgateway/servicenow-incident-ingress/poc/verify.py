#!/usr/bin/env python3
"""Exercise a deployed lab PoC through a loopback-only gateway port-forward.

Run on the lab host with KUBECONFIG already set. This performs two real model
invocations. Requires kubectl, bash, curl, jq, and the repository A2A helper.
It does not deploy resources or create ServiceNow records.
"""
import argparse
import datetime
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--helper", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    k = ["kubectl", "--context", args.context]

    def get(resource, namespace=None, name=None):
        command = k + ["get", resource]
        if name:
            command.append(name)
        if namespace:
            command += ["-n", namespace]
        return json.loads(subprocess.check_output(command + ["-o", "json"]))

    def post(path, body):
        request = urllib.request.Request(
            "http://127.0.0.1:18880" + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.status, response.read().decode(), time.monotonic() - started
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode(), time.monotonic() - started

    def inspect_a2a(response, expected):
        assert not response.get("error"), response.get("error")
        result = response["result"]
        assert result.get("status", {}).get("state") == "completed", result
        texts = []
        for artifact in result.get("artifacts", []):
            texts += [p["text"] for p in artifact.get("parts", []) if p.get("kind") == "text"]
        if not texts:
            for message in reversed(result.get("history", [])):
                if message.get("role") == "agent":
                    texts += [p["text"] for p in message.get("parts", []) if p.get("kind") == "text"]
                    break
        text = "\n".join(texts).strip()
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        output = json.loads(text)
        assert output["proof"] == "AGENT_RECEIVED_INCIDENT_JSON", output
        assert output["incident_number"] == expected["number"], output
        for field in ("priority", "short_description", "description", "nonce"):
            assert output[field] == expected[field], (field, output)
        return {"task_state": "completed", "agent_output": output, "task_id": result.get("id")}

    incident = json.loads((root / "incident.json").read_text())
    passed_incident = dict(incident, nonce="A2A_PASS_THROUGH_20261117")
    request = json.loads((root / "a2a-request.json").read_text())
    control_id = "incident-control-" + uuid.uuid4().hex
    request["params"]["message"]["messageId"] = control_id
    request["params"]["message"]["contextId"] = control_id
    params = evidence / "a2a-params.private.json"
    params.write_text(json.dumps(request["params"]))
    result = {
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "context": args.context,
        "sender": "Python client on Proxmox VM through loopback kubectl port-forward",
        "tests": [],
    }
    agent = get("agents.kagent.dev", "classic-agents", "incident-ingress-poc")
    result["agent"] = {
        "api_version": agent["apiVersion"],
        "name": agent["metadata"]["name"],
        "runtime": agent["spec"]["declarative"]["runtime"],
        "tools": agent["spec"]["declarative"].get("tools", []),
        "conditions": agent["status"]["conditions"],
    }
    gateway = get("deployments", "incident-ingress-poc", "incident-ingress-poc")
    controller = get("deployments", "classic-system", "classic-controller")
    result["images"] = {
        "gateway": gateway["spec"]["template"]["spec"]["containers"][0]["image"],
        "kagent_controller": controller["spec"]["template"]["spec"]["containers"][0]["image"],
    }
    result["argo_api_resources"] = subprocess.check_output(
        k + ["api-resources", "--api-group=argoproj.io", "--verbs=list", "-o", "name"], text=True
    ).splitlines()
    for resource in ("httproutes", "agentgatewaypolicies"):
        items = get(resource, "incident-ingress-poc")["items"]
        result[resource] = [
            {"name": item["metadata"]["name"], "generation": item["metadata"]["generation"],
             "status": item.get("status", {})} for item in items
        ]

    with (evidence / "port-forward.private.log").open("w") as log:
        process = subprocess.Popen(
            k + ["port-forward", "-n", "incident-ingress-poc", "svc/incident-ingress-poc",
                 "18880:8080", "--address=127.0.0.1"], stdout=log, stderr=log
        )
        try:
            for attempt in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Gateway port-forward exited")
                try:
                    with socket.create_connection(("127.0.0.1", 18880), timeout=1):
                        break
                except OSError:
                    time.sleep(0.25)
            else:
                raise RuntimeError("Gateway port-forward did not become reachable")

            receipt = evidence / "a2a-pass-through-response.private.json"
            invocation = subprocess.run(
                ["bash", str(args.helper.resolve()), "--url", "http://127.0.0.1:18880",
                 "--ns", "classic-agents", "--agent", "incident-ingress-poc",
                 "--payload-file", str(params), "--timeout", "90", "--receipt-file", str(receipt), "--json"],
                text=True, capture_output=True, timeout=100,
            )
            (evidence / "helper-output.private.txt").write_text(invocation.stdout + invocation.stderr)
            assert invocation.returncode == 0, invocation.stdout + invocation.stderr
            proof = inspect_a2a(json.loads(receipt.read_text()), passed_incident)
            result["tests"].append({"name": "a2a-pass-through", "passed": True, **proof})
            print("PASS: A2A pass-through returned the exact incident fields", flush=True)

            code, body, elapsed = post("/incidents/triage/", (root / "incident.json").read_bytes())
            (evidence / "raw-json-response.private.json").write_text(body)
            assert code == 200, (code, body)
            proof = inspect_a2a(json.loads(body), incident)
            result["tests"].append({"name": "raw-json-transformed-to-a2a", "http_status": code,
                                    "elapsed_seconds": round(elapsed, 3), "passed": True, **proof})
            print("PASS: raw JSON was transformed to A2A and the exact fields were returned", flush=True)

            for name, path, body in (
                ("malformed-json", "/incidents/triage/", b'{"number":'),
                ("unknown-route", "/unconfigured-path/", b'{}'),
            ):
                code, response, _ = post(path, body)
                assert code >= 400, (name, code, response)
                result["tests"].append({"name": name, "http_status": code,
                                        "response": response, "passed": True})
                print(f"PASS: {name} returned HTTP {code}", flush=True)
            result["passed"] = True
        except Exception as error:
            result["passed"] = False
            result["error"] = str(error)
            raise
        finally:
            process.terminate()
            process.wait(timeout=10)
            result["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            (evidence / "result.private.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
