#!/usr/bin/env bash
# Publish a navigable static portal for kagent-public HTML workgroup artifacts.

set -euo pipefail

PRIMARY_HOST="${KAGENT_PORTAL_PRIMARY_HOST:-{{KAGENT_PORTAL_SSH_TARGET}}}"
MIRROR_HOSTS="${KAGENT_PORTAL_MIRROR_HOSTS:-}"
REMOTE_DIR="${KAGENT_PORTAL_REMOTE_DIR:-{{KAGENT_PORTAL_REMOTE_DIR}}}"
PORT="${KAGENT_PORTAL_PORT:-8790}"
KUBE_CONTEXT="${KAGENT_PORTAL_KUBE_CONTEXT:-{{KUBE_CONTEXT}}}"
KUBE_NAMESPACE="${KAGENT_PORTAL_KUBE_NAMESPACE:-kagent-workgroup}"
KUBE_ENABLED="${KAGENT_PORTAL_KUBE_ENABLED:-true}"
KUBE_HOSTS="${KAGENT_PORTAL_HOSTS:-{{KAGENT_PORTAL_PRIMARY_HOSTNAME}} {{KAGENT_PORTAL_ALIAS_HOSTNAME}}}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

while IFS= read -r -d '' src; do
  rel="${src#"$ROOT"/}"
  dest="${rel//\//__}"
  cp "$src" "$STAGE/$dest"
done < <(
  find "$ROOT" \
    \( -path "$ROOT/.git" -o -path "$ROOT/node_modules" -o -path "$ROOT/.omc" \) -prune \
    -o -type f -name '*.html' -print0
)

PORTAL_ROOT="$STAGE" PORTAL_PORT="$PORT" python3 - <<'PY'
from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from pathlib import Path

portal = Path(os.environ["PORTAL_ROOT"])
port = os.environ["PORTAL_PORT"]

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean(value: str) -> str:
    value = TAG_RE.sub("", value)
    value = html.unescape(value)
    return SPACE_RE.sub(" ", value).strip()


def title_for(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
    for regex in (TITLE_RE, H1_RE):
        match = regex.search(text)
        if match:
            title = clean(match.group(1))
            if title:
                return title
    return path.stem.replace("-", " ").replace("_", " ").title()


def source_path_for(rel: str) -> str:
    return rel.replace("__", "/")


def group_for(rel: str) -> str:
    rel = source_path_for(rel)
    parts = Path(rel).parts
    if rel.startswith("docs/agentgateway"):
        return "Agent Gateway"
    if rel.startswith("docs/a2a"):
        return "A2A"
    if rel.startswith("docs/observability") or rel.startswith("observability/"):
        return "Observability"
    if rel.startswith("docs/security"):
        return "Security"
    if rel.startswith("ai-platform/"):
        return "AI Platform"
    if rel.startswith("agents/"):
        return "Agents"
    return parts[0].replace("-", " ").replace("_", " ").title() if parts else "Docs"


files = sorted(
    [p for p in portal.rglob("*.html") if p.name != "index.html"],
    key=lambda p: (group_for(str(p.relative_to(portal))), title_for(p).lower()),
)

cards = []
for path in files:
    rel = path.relative_to(portal).as_posix()
    stat = path.stat()
    updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    title = title_for(path)
    source_path = source_path_for(rel)
    group = group_for(rel)
    cards.append(
        '<button class="tab" data-src="{src}" data-group="{group}">'
        '<span>{title}</span><small>{group} / {updated} / {source_path}</small></button>'.format(
            src=html.escape(rel),
            group=html.escape(group),
            title=html.escape(title),
            updated=html.escape(updated),
            source_path=html.escape(source_path),
        )
    )

first = html.escape(files[0].relative_to(portal).as_posix()) if files else ""
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
count = str(len(files))

index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>kagent Workgroup</title>
  <style>
    :root {{
      --primary:#E60000;
      --secondary:#427C99;
      --accent:#F2BB3A;
      --background:#FFFFFF;
      --text:#1C1C1C;
      --grey-100:#F5F5F5;
      --grey-200:#E0E0E0;
      --grey-500:#7A7A7A;
      --grey-700:#444444;
      --base:4px;
      --radius:0px;
      --font:Frutiger, Arial, sans-serif;
    }}
    * {{ box-sizing:border-box; }}
    html, body {{ min-height:100%; }}
    body {{
      margin:0;
      background:var(--background);
      color:var(--text);
      font-family:var(--font);
      font-size:16.0016px;
      line-height:1.45;
      letter-spacing:0;
    }}
    a {{ color:var(--accent); }}
    .app {{
      min-height:100vh;
      display:grid;
      grid-template-columns:calc(var(--base) * 86) 1fr;
      background:var(--background);
    }}
    aside {{
      border-right:calc(var(--base) / 4) solid var(--grey-200);
      background:var(--grey-100);
      padding:calc(var(--base) * 5);
      display:flex;
      flex-direction:column;
      gap:calc(var(--base) * 4);
      min-width:0;
    }}
    main {{
      min-width:0;
      display:flex;
      flex-direction:column;
      background:var(--background);
    }}
    h1, h2 {{
      margin:0;
      font-family:var(--font);
      font-size:16.0016px;
      line-height:1.25;
      letter-spacing:0;
    }}
    .brand {{
      border-left:calc(var(--base) * 2) solid var(--primary);
      padding-left:calc(var(--base) * 3);
      display:grid;
      gap:calc(var(--base) * 2);
    }}
    .brand strong {{
      color:var(--primary);
      font-size:16.0016px;
      text-transform:uppercase;
      letter-spacing:0;
    }}
    p {{
      margin:0;
      color:var(--grey-700);
      font-size:16.0016px;
    }}
    .status {{
      display:grid;
      gap:calc(var(--base) * 2);
      border:calc(var(--base) / 4) solid var(--grey-200);
      border-radius:var(--radius);
      background:var(--background);
      padding:calc(var(--base) * 3);
    }}
    .status .row {{
      display:flex;
      justify-content:space-between;
      gap:calc(var(--base) * 3);
      color:var(--grey-700);
      font-size:16.0016px;
    }}
    .status b {{ color:var(--text); }}
    .tabs {{
      display:flex;
      flex-direction:column;
      gap:calc(var(--base) * 2);
      overflow:auto;
      padding-right:calc(var(--base) * 1);
    }}
    .tab {{
      width:100%;
      min-height:calc(var(--base) * 16);
      border:calc(var(--base) / 4) solid var(--grey-200);
      border-radius:var(--radius);
      background:var(--background);
      color:var(--text);
      cursor:pointer;
      display:flex;
      flex-direction:column;
      justify-content:center;
      gap:calc(var(--base) * 1);
      padding:calc(var(--base) * 3);
      text-align:left;
      font:inherit;
    }}
    .tab:hover, .tab.active {{
      border-color:var(--primary);
      box-shadow:inset calc(var(--base) * 1) 0 0 var(--primary);
    }}
    .tab span {{
      font-weight:700;
      overflow-wrap:anywhere;
    }}
    .tab small {{
      color:var(--grey-500);
      font-size:13px;
      line-height:1.25;
    }}
    .topbar {{
      min-height:calc(var(--base) * 16);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:calc(var(--base) * 4);
      padding:calc(var(--base) * 3) calc(var(--base) * 5);
      border-bottom:calc(var(--base) / 4) solid var(--grey-200);
      background:var(--background);
    }}
    .topbar strong {{
      min-width:0;
      color:var(--primary);
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }}
    .open {{
      color:var(--text);
      background:var(--accent);
      border:calc(var(--base) / 4) solid var(--accent);
      border-radius:var(--radius);
      padding:calc(var(--base) * 2) calc(var(--base) * 3);
      text-decoration:none;
      white-space:nowrap;
      font-weight:700;
    }}
    iframe {{
      flex:1;
      width:100%;
      border:0;
      background:var(--background);
    }}
    .empty {{
      padding:calc(var(--base) * 6);
      color:var(--primary);
    }}
    @media (max-width: 860px) {{
      .app {{ grid-template-columns:1fr; }}
      aside {{ border-right:0; border-bottom:calc(var(--base) / 4) solid var(--grey-200); }}
      .tabs {{ max-height:calc(var(--base) * 60); }}
      iframe {{ min-height:75vh; }}
      .topbar {{ align-items:flex-start; flex-direction:column; }}
      .topbar strong {{ white-space:normal; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand">
        <strong>kagent</strong>
        <h1>Workgroup HTML Portal</h1>
        <p>Single click-through surface for public-ready demos, explainers, security notes, observability playbooks, and platform knowledge work.</p>
      </div>
      <div class="status" aria-label="portal status">
        <div class="row"><span>Pages</span><b>{html.escape(count)}</b></div>
        <div class="row"><span>Primary host</span><b>Geekom</b></div>
        <div class="row"><span>Fallback port</span><b>{html.escape(str(port))}</b></div>
        <div class="row"><span>Updated</span><b>{html.escape(now)}</b></div>
      </div>
      <nav class="tabs" aria-label="kagent HTML pages">{''.join(cards) or '<p>No HTML pages published yet.</p>'}</nav>
    </aside>
    <main>
      <div class="topbar">
        <strong id="current">kagent page</strong>
        <a class="open" id="open" href="{first}" target="_blank" rel="noreferrer">Open full page</a>
      </div>
      {f'<iframe id="frame" src="{first}" title="Selected kagent workgroup page"></iframe>' if first else '<div class="empty">No HTML pages found.</div>'}
    </main>
  </div>
  <script>
    const frame = document.getElementById('frame');
    const label = document.getElementById('current');
    const open = document.getElementById('open');
    const tabs = [...document.querySelectorAll('.tab')];
    function activate(tab) {{
      tabs.forEach((item) => item.classList.remove('active'));
      tab.classList.add('active');
      const src = tab.dataset.src;
      frame.src = src;
      open.href = src;
      label.textContent = tab.querySelector('span').textContent;
      history.replaceState(null, '', '#' + encodeURIComponent(src));
    }}
    tabs.forEach((tab) => tab.addEventListener('click', () => activate(tab)));
    const wanted = decodeURIComponent(location.hash.replace(/^#/, ''));
    const selected = tabs.find((tab) => tab.dataset.src === wanted) || tabs[0];
    if (selected) activate(selected);
  </script>
</body>
</html>
"""

portal.joinpath("index.html").write_text(index, encoding="utf-8")
PY

publish_host() {
  local host="$1"
  local required="$2"

  if ! ssh -o ConnectTimeout=6 "$host" "true" >/dev/null 2>&1; then
    if [[ "$required" == "required" ]]; then
      echo "ERROR: primary kagent portal host unreachable: $host" >&2
      return 1
    fi
    echo "skip offline mirror: $host"
    return 0
  fi

  ssh "$host" "mkdir -p '$REMOTE_DIR'"
  rsync -az --delete "$STAGE"/ "$host:$REMOTE_DIR/"

  ssh "$host" "mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/kagent-workgroup-portal.service <<EOF
[Unit]
Description=kagent workgroup HTML portal
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REMOTE_DIR
ExecStart=/usr/bin/python3 -m http.server $PORT --bind 0.0.0.0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now kagent-workgroup-portal.service >/dev/null
systemctl --user restart kagent-workgroup-portal.service"

  if [[ "$KUBE_ENABLED" == "true" ]]; then
    ssh "$host" "if command -v kubectl >/dev/null 2>&1; then
kubectl --context '$KUBE_CONTEXT' get ns '$KUBE_NAMESPACE' >/dev/null 2>&1 || kubectl --context '$KUBE_CONTEXT' create ns '$KUBE_NAMESPACE' >/dev/null
cd '$REMOTE_DIR'
kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' delete configmap kagent-workgroup-static >/dev/null 2>&1 || true
kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' create configmap kagent-workgroup-static --from-file=. >/dev/null
kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' apply -f - >/dev/null <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kagent-workgroup-portal
  namespace: $KUBE_NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kagent-workgroup-portal
  template:
    metadata:
      labels:
        app: kagent-workgroup-portal
    spec:
      containers:
      - name: nginx
        image: nginx:1.27-alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: static
          mountPath: /usr/share/nginx/html
          readOnly: true
      volumes:
      - name: static
        configMap:
          name: kagent-workgroup-static
---
apiVersion: v1
kind: Service
metadata:
  name: kagent-workgroup-portal
  namespace: $KUBE_NAMESPACE
spec:
  selector:
    app: kagent-workgroup-portal
  ports:
  - name: http
    port: 80
    targetPort: 80
YAML
for portal_host in $KUBE_HOSTS; do
cat <<YAML | kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' apply -f - >/dev/null
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kagent-workgroup-\${portal_host//./-}
  namespace: $KUBE_NAMESPACE
spec:
  ingressClassName: traefik
  rules:
  - host: \$portal_host
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kagent-workgroup-portal
            port:
              number: 80
YAML
done
kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' rollout restart deploy/kagent-workgroup-portal >/dev/null
kubectl --context '$KUBE_CONTEXT' -n '$KUBE_NAMESPACE' rollout status deploy/kagent-workgroup-portal --timeout=60s >/dev/null
fi"
  fi

  echo "published: $host:$REMOTE_DIR on port $PORT"
}

publish_host "$PRIMARY_HOST" required

for host in $MIRROR_HOSTS; do
  publish_host "$host" optional
done
