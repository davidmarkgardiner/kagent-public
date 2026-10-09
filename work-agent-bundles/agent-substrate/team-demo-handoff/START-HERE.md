# Copy this folder for the Substrate team demo

Copy the **entire `team-demo-handoff` folder** to the workstation or private
work-agent project. All files needed for the 0.0.9/0.10.x audit, synthetic
`SandboxAgent` session demo, presenter script, and Markdown evidence package
are directly in this folder. Preserve the filenames. The demo runner reads
`sandboxagent-demo.yaml` beside itself; it will not work if only the Markdown
files are copied.

## Start here

1. Read [`HANDS-ON-WALKTHROUGH.md`](HANDS-ON-WALKTHROUGH.md) and check the exact
   installed version. It has the operator commands and four presenter pauses.
2. Give [`WORK-AGENT-DEMO-HANDOFF.md`](WORK-AGENT-DEMO-HANDOFF.md) to the work
   agent. It asks for four completed **private** Markdown files and links to
   the included templates.
   If the golden actor fails with `NotFound`, give it
   [`GOLDEN-ACTOR-NOT-FOUND-NEXT-STEP.md`](GOLDEN-ACTOR-NOT-FOUND-NEXT-STEP.md)
   before any further rehearsal.
3. Run [`audit-substrate-install.sh`](audit-substrate-install.sh) from this
   folder before creating a canary. If required CRDs or components are absent,
   stop and record the failure.
4. For the live sequence, run [`run-memory-demo.sh`](run-memory-demo.sh). It
   reads [`sandboxagent-demo.yaml`](sandboxagent-demo.yaml) and writes a private
   `receipts/` directory. Copy [`RECEIPT-TEMPLATE.md`](RECEIPT-TEMPLATE.md)
   into a completed private note.

These scripts need `kubectl`, `jq`, `curl`, a named kube context, and an
approved reachable ModelConfig. The presenter run also needs a terminal and
the kagent UI or equivalent actor inventory. The cluster must already have
the compatible Substrate/kagent control plane, CRDs, WorkerPool, snapshot
store, and gVisor asset. **This folder does not contain Helm charts, images,
the `runsc` executable, credentials, or a cluster installation.** The
[`AIRGAPPED-AKS-README.md`](AIRGAPPED-AKS-README.md) and
[`PACKAGE-AND-PRESEED.md`](PACKAGE-AND-PRESEED.md) explain those deployment
inputs for the work agent's version-matched redeploy document.

## Files in the folder

| Purpose | Files |
| --- | --- |
| Presenter and work-agent instructions | `HANDS-ON-WALKTHROUGH.md`, `WORK-AGENT-DEMO-HANDOFF.md` |
| Golden actor failure triage | `GOLDEN-ACTOR-NOT-FOUND-NEXT-STEP.md` |
| Runnable canary | `audit-substrate-install.sh`, `run-memory-demo.sh`, `sandboxagent-demo.yaml` |
| Extra read-only installation check | `verify-aks-substrate.sh` |
| Private Markdown output templates | `RECEIPT-TEMPLATE.md`, `WORKPLACE-SUBSTRATE-KAGENT-PROOF-TEMPLATE.md`, `WORKPLACE-SUBSTRATE-GITLAB-TICKET-TEMPLATE.md`, `WORKPLACE-SUBSTRATE-REDEPLOY-WALKTHROUGH-TEMPLATE.md` |
| Public example and deployment references | `HOME-LAB-SUBSTRATE-PROOF-EXAMPLES.md`, `LIVE-RUN-2026-09-14.md`, `RUN-RED-2026-07-16.md`, `AIRGAPPED-AKS-README.md`, `PACKAGE-AND-PRESEED.md`, `AKS-EVAL-WORK-AGENT-HANDOFF.md`, `WORK-AGENT-RUNSC-EQUIVALENCE-HANDOFF.md` |

`CHECKSUMS.sha256` covers the copied files. Check it after transfer with
`shasum -a 256 -c CHECKSUMS.sha256` on macOS or `sha256sum -c CHECKSUMS.sha256`
on Linux. `receipts/` is ignored by Git in this folder; store those raw
private results only in the approved evidence location.

The full source branch is
https://github.com/davidmarkgardiner/kagent-public/tree/docs/substrate-workplace-proof-20261009/work-agent-bundles/agent-substrate/team-demo-handoff
