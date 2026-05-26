# kagent Workgroup Portal

The kagent workgroup HTML portal collects standalone HTML artifacts from this
repository into one click-through surface.

Primary URL:

- <https://{{KAGENT_PORTAL_PRIMARY_HOSTNAME}}/>

Alias:

- <https://{{KAGENT_PORTAL_ALIAS_HOSTNAME}}/>

Direct Geekom fallback:

- <http://{{KAGENT_PORTAL_FALLBACK_HOST}}:{{KAGENT_PORTAL_PORT}}/>

Refresh it after adding or changing HTML pages:

```bash
scripts/publish-kagent-workgroup-portal.sh
```

The publisher:

- scans `kagent-public` for `*.html`
- builds a red/grey Frutiger/Arial static index
- copies the portal to `{{KAGENT_PORTAL_REMOTE_DIR}}`
- restarts `{{KAGENT_PORTAL_SYSTEMD_SERVICE}}` on the configured portal host
- refreshes the `kagent-workgroup` Kubernetes namespace and Traefik ingress

Related portals:

- General Agentic OS: <https://{{AGENTIC_OS_PORTAL_HOSTNAME}}/>
- Trading: <https://{{TRADING_PORTAL_HOSTNAME}}/>
