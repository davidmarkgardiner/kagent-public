# parse-bigpanda.jq
#
# Normalises a BigPanda outbound webhook payload into the same internal shape
# used by parse-alertmanager (prometheus-alerting/04-workflow-template.yaml).
#
# Input:  BigPanda incident webhook JSON (root object with .incident_id, .alerts[])
# Output: JSON array of normalised alert objects, one per BigPanda alert
#
# Internal shape (must match what kagent-triage workflow expects):
#   {
#     "alertname":   string,   # what fired
#     "namespace":   string,   # CRITICAL — agent routing key
#     "pod":         string,   # may be empty for non-pod alerts
#     "cluster":     string,
#     "environment": string,
#     "severity":    string,   # "critical" | "warning" | "unknown"
#     "status":      string,   # "firing" | "resolved"
#     "summary":     string,
#     "description": string,
#     "runbook_url": string,
#     "source_url":  string,   # link back to the alert in Grafana/AM
#     "incident_url":string,   # BigPanda incident URL
#     "started_at":  string,   # ISO8601 (converted from Unix epoch)
#     "age_minutes": number
#   }
#
# SPIKE REQUIRED: field paths below are based on the expected BigPanda schema.
# Run against a real payload and update any paths marked "⚠️ verify".

.alerts[]
| . as $alert
| {
    # ── Identity ─────────────────────────────────────────────────────────────
    # BigPanda uses .check as alertname (⚠️ verify: some sources use .tags.alertname)
    alertname: (
      .tags.alertname                     # explicit tag if AM source maps it
      // .check                           # BigPanda native field
      // "unknown"
    ),

    # ── Routing key — CRITICAL ────────────────────────────────────────────────
    # namespace MUST survive for agent routing. If this is empty, the workflow
    # cannot route to the right specialist agent and will fall back to sre-triage-agent.
    # Platform team MUST configure BigPanda Prometheus source to pass namespace as a tag.
    namespace: (
      .tags.namespace                     # ⚠️ verify: may be absent without BP source config
      // ""
    ),

    # ── Object identity ───────────────────────────────────────────────────────
    pod: (
      .tags.pod                           # ⚠️ verify
      // .tags.instance                   # fallback: Prometheus instance label
      // ""
    ),

    # BigPanda uses .host as the primary grouping (often the cluster name or node).
    # .tags.cluster is the explicit label if AM source is configured correctly.
    cluster: (
      .tags.cluster                       # ⚠️ verify
      // .host                            # BigPanda native (may be node, not cluster)
      // "unknown"
    ),

    environment: (
      .tags.environment                   # ⚠️ verify
      // "unknown"
    ),

    # ── Severity ──────────────────────────────────────────────────────────────
    # BigPanda remaps to its own scale. Prefer the original Prometheus label.
    severity: (
      .tags.severity_original             # original Prometheus severity label
      // .severity                        # BigPanda severity (critical/warning/unknown)
      // "warning"
    ),

    # ── Status ────────────────────────────────────────────────────────────────
    # BigPanda uses "active"/"inactive" not "firing"/"resolved".
    # Map to the same strings the rest of the workflow uses.
    status: (
      if .status == "active" then "firing"
      elif .status == "inactive" then "resolved"
      else .status
      end
    ),

    # ── Human-readable context ────────────────────────────────────────────────
    summary: (
      .tags.summary                       # ⚠️ verify
      // .description                     # BigPanda native description
      // ""
    ),

    description: (
      .description                        # BigPanda native (mapped from AM annotations.description)
      // .tags.description                # ⚠️ verify
      // ""
    ),

    runbook_url: (
      .tags.runbook_url                   # ⚠️ verify
      // ""
    ),

    # ── Source links ─────────────────────────────────────────────────────────
    # generator_url = link back to Grafana Explore / AlertManager source query
    source_url: (
      .tags.generator_url                 # ⚠️ verify — often not forwarded by BigPanda
      // .tags.external_url               # AlertManager UI link
      // ""
    ),

    # BigPanda incident URL (link to correlated view — more useful than per-alert)
    incident_url: ($alert | input_line_number | . as $dummy | "" )  # placeholder — replace below

  }
# Attach the incident-level URL (available on root, not per-alert).
# Run this filter with:  jq --argjson root_incident_url "$INCIDENT_URL" -f parse-bigpanda.jq
# Or pipe through a wrapper that injects it — see workflow-template-bigpanda.yaml.

# ── Time fields ───────────────────────────────────────────────────────────────
# BigPanda uses Unix epoch integers; convert to ISO8601 for consistency.
| . + {
    started_at: (
      .started_at
      | if type == "number" then
          # jq doesn't have strftime on all builds; format manually
          # Workflow step uses: date -d @<epoch> --iso-8601=seconds
          # So we pass the raw epoch as a string and let the shell convert it.
          tostring
        else
          .
        end
    ),
    age_minutes: (
      .started_at
      | if type == "number" then
          # Approximate: workflow compares against NOW at execution time
          # Pass through raw epoch; let the shell do: echo "($(date +%s) - $started_at) / 60" | bc
          .
        else
          0
        end
    )
  }
