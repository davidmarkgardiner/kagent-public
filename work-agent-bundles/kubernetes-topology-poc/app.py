"""Local read-only topology viewer and bounded agent-query prototype."""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from topology import collect, neighborhood

HERE = Path(__file__).parent


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="explicit non-production kube context")
    parser.add_argument("--knowledge", type=Path, help="curated local JSON guidance mappings")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=int, default=30, help="poll interval in seconds, minimum 10")
    parser.add_argument("--once", action="store_true", help="print a JSON snapshot and exit")
    parser.add_argument("--query", help="resource ID for one bounded neighborhood query")
    parser.add_argument("--depth", type=int, default=1)
    return parser.parse_args()


def load_knowledge(path):
    if not path:
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("knowledge mapping must be a JSON list")
    return data


def main():
    args = arguments()
    if args.interval < 10:
        raise SystemExit("--interval must be at least 10 seconds")
    knowledge = load_knowledge(args.knowledge)
    graph = collect(args.context, knowledge)
    if args.query:
        print(json.dumps(neighborhood(graph, args.query, args.depth), indent=2))
        return
    if args.once:
        print(json.dumps(graph, indent=2))
        return

    state = {"graph": graph}
    lock = threading.Lock()

    def refresh():
        while True:
            time.sleep(args.interval)
            refreshed = collect(args.context, knowledge)
            with lock:
                # An incomplete refresh must never silently turn a prior green
                # view into an apparently current partial inventory.
                state["graph"] = refreshed

    threading.Thread(target=refresh, daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") not in (f"127.0.0.1:{args.port}", f"localhost:{args.port}"):
                self.send_error(403, "localhost only")
                return
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = (HERE / "index.html").read_bytes()
                content_type = "text/html; charset=utf-8"
                status = 200
            elif parsed.path == "/api/graph":
                with lock:
                    payload = state["graph"]
                body = json.dumps(payload).encode()
                content_type, status = "application/json", 200
            elif parsed.path == "/api/neighbors":
                params = parse_qs(parsed.query)
                try:
                    identifier = params.get("id", [""])[0]
                    depth = int(params.get("depth", ["1"])[0])
                    with lock:
                        payload = neighborhood(state["graph"], identifier, depth)
                    body, status = json.dumps(payload).encode(), 200
                except (ValueError, OverflowError) as error:
                    body, status = json.dumps({"error": str(error)}).encode(), 400
                content_type = "application/json"
            else:
                body, content_type, status = b"not found", "text/plain", 404
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    # Localhost only: this proof has no authentication or user-specific RBAC.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Topology viewer: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
