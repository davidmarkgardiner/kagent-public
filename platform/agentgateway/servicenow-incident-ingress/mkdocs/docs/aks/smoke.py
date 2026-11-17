#!/usr/bin/env python3
"""Send exactly one synthetic HTTPS POST. No retries, redirects, or deployments."""
import argparse
import datetime
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        return None


def assess(code, body, expected):
    if code != 200:
        raise ValueError("HTTP " + str(code) + "; inspect the private receipt")
    response = json.loads(body)
    if not isinstance(response, dict):
        raise ValueError("Expected a JSON-RPC response object")
    if response.get("error"):
        raise ValueError("JSON-RPC error; inspect the private receipt")
    result = response.get("result", {})
    if not isinstance(result, dict):
        raise ValueError("Expected an A2A task object")
    state = result.get("status", {}).get("state")
    if state != "completed":
        raise ValueError(f"A2A task state is {state!r}; completed agent execution is not proved")
    texts = [part["text"] for artifact in result.get("artifacts", [])
             for part in artifact.get("parts", []) if part.get("kind") == "text"]
    if not texts:
        for message in reversed(result.get("history", [])):
            if message.get("role") == "agent":
                texts = [part["text"] for part in message.get("parts", []) if part.get("kind") == "text"]
                break
    if not any(text.strip() for text in texts):
        raise ValueError("Completed task has no agent response text")
    if any(value not in "\n".join(texts) for value in expected):
        raise ValueError("Expected marker is missing from agent output")
    return {"task_state": state, "task_id": result.get("id"), "expected_markers_found": len(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--headers-file", type=Path)
    parser.add_argument("--request", type=Path, default=Path(__file__).with_name("incident.json"))
    parser.add_argument("--out", type=Path, default=Path("evidence"))
    parser.add_argument("--timeout", type=int, default=110)
    parser.add_argument("--expect-text", action="append", default=[])
    args = parser.parse_args()
    url = urllib.parse.urlsplit(args.url)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        parser.error("Use the actual HTTPS endpoint, without credentials, query or fragment")
    if not 1 <= args.timeout <= 600:
        parser.error("Timeout must be from 1 to 600 seconds")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if args.headers_file:
        extra = json.loads(args.headers_file.read_text())
        if not isinstance(extra, dict) or any(not isinstance(k, str) or not isinstance(v, str) or "{{" in v for k, v in extra.items()):
            parser.error("Fill the local header values using the approved caller identity")
        headers.update(extra)
    payload = args.request.read_bytes()
    json.loads(payload)
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Use an empty output folder to preserve previous evidence")
    args.out.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(args.url, data=payload, headers=headers, method="POST")
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(request, timeout=args.timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        code = response.code
        body = response.read(256 * 1024 + 1)
    (args.out / "response.private.txt").write_bytes(body)
    (args.out / "request.private.json").write_bytes(payload)
    receipt = {"observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "http_status": code}
    try:
        if len(body) > 256 * 1024:
            raise ValueError("Response exceeded 256 KiB; no completion claim")
        receipt.update(assess(code, body, args.expect_text))
        receipt["passed"] = True
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        receipt.update(passed=False, error=str(error))
    (args.out / "result.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PASS: completed A2A response and markers verified" if receipt["passed"] else "FAIL: " + receipt["error"])
    print("Private receipts saved in " + str(args.out))
    raise SystemExit(0 if receipt["passed"] else 1)


if __name__ == "__main__":
    main()
