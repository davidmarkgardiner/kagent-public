# Peer Review — `ai-platform/kagent-knowledge-base`

**Reviewer:** Claude (Opus 4.7)
**Date:** 2026-05-14
**Scope:** Full directory — docs, manifests, scripts, evidence tooling.

---

## Overall verdict

Solid POC. The design is clean, the safety posture is intentional, and the
upstream `doc2vec` + `querydoc` MCP pattern is a much better fit than rolling
custom retrieval. The split between indexer (RW) and querydoc (RO) on a
shared PVC mirrors the kagent reference shape, and the suspended CronJob +
dedicated secret + dedicated `ModelConfig` are the right defaults for a
demo.

Most of the feedback below is hardening, consistency, and production-readiness
nits. Two items I would resolve before promoting beyond POC:
[L1 — CronJob is openai-only](#l1) and
[S1 — no `securityContext` anywhere](#s1).

---

## Logic / correctness findings

### <a id="l1"></a>L1 — CronJob hard-codes `EMBEDDING_PROVIDER=openai`

`k8s/indexer-cronjob.yaml:38` sets the provider to `openai` and inlines a
config that only references `openai.*`. The local builder (`scripts/build-platform-kb-db.sh`)
supports `azure`, and `EMBEDDING-OPTIONS.md` advertises Azure + local OpenAI-compatible
endpoints — but the cluster-side indexer can't reach them. If anyone reuses
the documented Azure path, then unsuspends the CronJob, the embeddings will
fail (or worse, succeed with the wrong dimension and silently produce an
incompatible DB).

Recommendation: pull `EMBEDDING_PROVIDER` from a ConfigMap and switch the
inline config the same way the build script does, or document explicitly
that cluster refresh is OpenAI-only and the Azure path is local-builder-only.

### L2 — `$VAR` substitution in `config.yaml` relies on `doc2vec` runtime expansion

`config/doc2vec-platform-kb.yaml:5` writes `api_key: '${OPENAI_API_KEY}'` as a
literal string. The build script `cp`s this file verbatim into the doc2vec
workdir and runs `npm start`. Two paths assume the same thing:

- the local build (`scripts/build-platform-kb-db.sh:78`)
- the CronJob's inline heredoc (`k8s/indexer-cronjob.yaml:62-83`, single-quoted
  `'EOF'` — no shell expansion)

Both depend on `doc2vec` doing its own `${VAR}` expansion at config-load.
If upstream `doc2vec` ever drops that behavior, every embedding call sends a
literal `${OPENAI_API_KEY}` string and you get an opaque 401 instead of a
clear "auth not configured" error.

Recommendation: add a `validate.sh` step that greps the rendered config for
unexpanded `${...}` after a dry-run env load, or expand at build time
(`envsubst < config.yaml`).

### L3 — Embedding-failure grep can miss real failures

`scripts/build-platform-kb-db.sh:88` and `k8s/indexer-cronjob.yaml:88`
filter for embedding errors with:

```
"incorrect api key|401 unauthorized|error generating embeddings|...|^error:"
```

`^error:` only matches start-of-line. Real `doc2vec` output is often
`[2026-01-01T10:00:00.000Z] error: ...` which won't be caught. Recommend
dropping the `^` anchor or adding `\berror:` / `[Ee]rror:` patterns.

The intent — "doc2vec leaves a non-empty SQLite even after embedding
failure, so refuse to publish" — is good. The README calls this out
explicitly, which I appreciate; it's the kind of footgun worth surfacing.

### L4 — `RemoteMCPServer.timeout: 10s` is tight

`k8s/remotemcpserver.yaml:12`. Vector-search round trip is:
embed-the-query (OpenAI HTTP, 1–3s) + SQLite vector scan (<1s) + MCP
response assembly. Under cold start, 10s is on the edge. `sseReadTimeout`
is 5m, so streaming is fine; this is the request-establish timeout. Bump
to 30s.

### L5 — `backoffLimit: 1` is aggressive for an embedding job

`k8s/indexer-cronjob.yaml:16`. OpenAI 429s are normal; a single retry is
the difference between "nightly refresh worked" and "stale DB until someone
notices." Recommend `backoffLimit: 3` plus `concurrencyPolicy: Forbid`
(already set).

### L6 — `kubectl run --overrides` for the seed pod is fragile

`scripts/deploy-poc-demo.sh:58-61`. Works today but `--overrides` is
deprecated-adjacent and the JSON-on-CLI shape is easy to corrupt. A small
seed manifest under `k8s/seed/` applied with `kubectl apply -f` + delete
afterward is more robust. Not blocking.

### L7 — `awk` kind/name parser in validate.sh is YAML-fragile

`scripts/validate.sh:71`. Works for the current rendered output, but YAML
ordering (`kind:` before `metadata.name:`) is not guaranteed. `yq e
'[kind, metadata.name] | @tsv'` would be safer.

### L8 — Sanitize regex only catches OpenAI key shape

`scripts/capture-evidence.sh:11`:
`sed -E 's/sk-[A-Za-z0-9_*.-]{6,}/sk-***/g'`. Azure OpenAI keys (32-char
hex) and bearer tokens won't be redacted. If you ever capture evidence with
`EMBEDDING_PROVIDER=azure`, the key can leak into `EVIDENCE.md`. Add an
explicit Azure-key pattern or redact `AZURE_OPENAI_KEY` env var separately
from the preflight log.

---

## Security / hardening findings

### <a id="s1"></a>S1 — No `securityContext` on any workload

Neither `k8s/indexer-cronjob.yaml` nor `k8s/querydoc-deployment.yaml`
specifies a pod or container `securityContext`. If the `kagent` namespace
is labelled `pod-security.kubernetes.io/enforce: restricted` (PSS), neither
pod will admit. Even if not, both run as root by default.

Add to both:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65532
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: ...
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

The indexer container does `apt-get install`, which requires writable
`/var`. Keep `readOnlyRootFilesystem: false` *only* on the indexer, or
better: switch to an image with git pre-baked (see I1) and turn rootFS
read-only on both.

### S2 — `automountServiceAccountToken` not disabled

Neither workload talks to the Kubernetes API. Both auto-mount the default
SA token. Add `automountServiceAccountToken: false` at pod spec level.

### S3 — No `NetworkPolicy` for the namespace

`querydoc` accepts traffic from anywhere in the cluster. For a POC, fine.
For production, scope ingress to the `kagent` controller / agent pods and
deny all else.

### S4 — `kagent-builtin-prompts` ConfigMap is an undeclared prerequisite

`k8s/platform-knowledge-agent.yaml:31-34` references a ConfigMap that
must exist already (kagent installs it). If kagent isn't installed first,
the Agent reconciles into a failed state. Worth adding a one-liner in the
README under prerequisites.

---

## Infra / reliability findings

### I1 — Indexer does `apt-get install git` on every run

`k8s/indexer-cronjob.yaml:51-53`. Costs 30–60s of cold-start network I/O
on every nightly run and breaks if Debian mirrors are down. Use
`node:20-bookworm` (git pre-installed) or a small custom image with git +
node baked. Or run an init container `image: alpine/git` to clone, then
hand off to `node:20-alpine` for the build.

### I2 — Single PVC + `ReadWriteOnce` couples indexer and querydoc to one node

`k8s/pvc.yaml:9`. If the cluster's default StorageClass is topology-aware
or zonal, the indexer Job may schedule on a node that the querydoc pod
can't follow (RWO blocks multi-attach). On a single-node homelab
this is fine; document the constraint, or move to RWX / object-storage
artifact handoff for multi-node clusters.

### I3 — No `livenessProbe` on querydoc

`k8s/querydoc-deployment.yaml`. Startup + readiness only. If the MCP
server deadlocks while still answering `/health` it never restarts. Add a
liveness probe with a longer interval (e.g., 60s) and a higher failure
threshold than readiness.

### I4 — `appProtocol: mcp` is non-standard

`k8s/querydoc-service.yaml:18`. Kubernetes accepts any string here, but
most service meshes (Linkerd, Istio) only recognize a known set
(`http`, `http2`, `grpc`, `tcp`, ...). If you ever mesh this namespace,
expect surprises. `http` is the truthful value.

### I5 — `maxTokens: 1200` may truncate citation-heavy answers

`k8s/modelconfig.yaml:16`. Each answer cites multiple `file://...` paths
+ headings. 1200 tokens is ~900 words; tight for an answer that retrieves
3–5 chunks. Recommend 2000.

### I6 — `evidence/rendered-platform-kb.yaml` is checked-in but will drift

The file is a snapshot of `kustomize build k8s` at one point in time. It's
useful as a baseline for diffing, but a CI step (or `validate.sh` mode) to
regenerate-and-diff would prevent it going stale silently.

---

## Documentation findings

### D1 — `validate.sh` requires `rg` but README doesn't say so

`scripts/validate.sh:63` shells out to `rg` (ripgrep). On a fresh host
without ripgrep the safety scan fails with a confusing "command not found."
Either fall back to `grep -E` or add a prerequisites note.

### D2 — README "Safety" section is good — keep it

The explicit "do not apply to `kind-argo-workflow`" and the listing of
created kinds matches the repo's broader public-safety posture (per
`AGENTS.md`). Worth replicating in any future POC under `ai-platform/`.

### D3 — `EMBEDDING-OPTIONS.md` is excellent

Clear, includes the local OpenAI-compatible route, calls out the
dimension-must-match-DB constraint explicitly. The "rebuild
platform-kb.db whenever changing embedding model or dimension"
warning is the kind of guidance future-self will thank you for.

### D4 — Mention `kagent-builtin-prompts` ConfigMap as a prerequisite

See S4. The README's "Kubernetes Deployment Flow" section assumes kagent
is already installed; one explicit prerequisite line covers it.

### D5 — Agent Query Contract — consider adding a negative example

README §"Agent Query Contract" tells the agent what to do; it doesn't
spell out what *not* to do. The system message in
`platform-knowledge-agent.yaml:48-50` already says "do not push to Git,
do not create Azure resources." Worth mirroring that constraint into the
README so a reader doesn't have to read the Agent CR to learn it.

---

## Style / consistency nits (non-blocking)

- `build-platform-kb-db.sh:17` uses `[ -z ]` for the openai check;
  `:22-25` uses `${VAR:?...}` parameter expansion for azure. Pick one.
- `evidence/README.md` lists `EVIDENCE.md` and `rendered-platform-kb.yaml`
  as outputs, but `capture-evidence.sh` also writes `doc2vec-preflight.log`.
  Add it to the list.
- `config/querydoc-env.example` has a trailing blank line and `OPENAI_API_KEY=replace-me`
  on the first line — fine, but the `KAGENT_LOG_LEVEL=info` line is unique
  to querydoc and worth a one-line comment.
- `app.kubernetes.io/part-of: kagent` is a generic label; the
  `deploy-poc-demo.sh:75` `get -l part-of=kagent` selector will match
  anything else in the namespace using the same label. Consider a more
  specific selector like `app.kubernetes.io/name in (platform-kb,...)`.

---

## What's good (worth keeping)

- Dedicated `platform-kb-openai` Secret + `ModelConfig` — doesn't leak into
  the shared cluster default model config.
- `suspend: true` on the CronJob by default.
- Two-tier health gates: `startupProbe` with high `failureThreshold` for
  cold start, then `readinessProbe` for steady-state. Good shape.
- `readOnly: true` mount on querydoc volume — DB can't be corrupted by the
  reader.
- `validate.sh` safety scan that fails on Azure/KRO provisioning kinds —
  exactly the right guardrail for this repo.
- Refuse-to-publish-on-embedding-failure logic in the builder is the kind
  of paranoia that pays off later.
- Live-demo evidence capture (`capture-live-demo-evidence.sh`) actually
  exercises the A2A path end-to-end and asserts on tool calls + source
  citation — that's real verification, not a smoke test cosplay.

---

## Suggested follow-up order

1. [S1] Add `securityContext` to both pods.
2. [L1] Decide: cluster indexer stays openai-only (document), or
   parameterize the provider.
3. [I1] Bake git into the indexer image.
4. [L4] Bump `RemoteMCPServer.timeout` to 30s.
5. [D1] Add prerequisites to README (`rg`, kustomize/kubectl, kagent
   installed with `kagent-builtin-prompts` ConfigMap present).
6. Everything else is polish.
