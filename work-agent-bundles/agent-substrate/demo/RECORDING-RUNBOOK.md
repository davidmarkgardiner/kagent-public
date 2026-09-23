# Agent Substrate short capture runbook

**Status:** prepared input only, not a verified runtime receipt  
**Target:** the authorized `red` environment, using only synthetic resources and a pinned current kagent and Agent Substrate version

## Before recording

- Use the existing `kagent` namespace and synthetic resource names.
- Confirm the active context is exactly `red` before every mutation.
- Pin and record the kagent, Agent Substrate, controller and CRD versions.
- Confirm `kagent-default` exists in `kagent` and has capacity.
- Confirm `default-model-config` is a safe test model configuration.
- Hide terminal history, cloud account information, kubeconfig paths, usernames and private endpoints.
- Capture the source revision used to build or install the environment.

Do not run the supplied manifest against an unknown context. The operator must name and inspect the exact context before any apply.

## Recording sequence

### 1. Establish the resource model

Show only the relevant fields from `sandboxagent.yaml`:

- `kind: SandboxAgent`
- `spec.declarative.runtime`
- `spec.substrate.workerPoolRef`

Explain that the `SandboxAgent` declaration is reconciled into an Agent Substrate `ActorTemplate` and uses a `WorkerPool` for execution capacity.

### 2. Apply and reconcile

Apply the manifest through the chosen public-safe GitOps or controlled demo path. Record:

- `SandboxAgent` Accepted and Ready conditions;
- generated `ActorTemplate` phase;
- `WorkerPool` desired and available capacity;
- exact timestamps.

### 3. Prove first execution

Create a new synthetic session context, `demo-session-01`. Ask the agent to remember the marker `ORANGE-FALCON-17`. Record:

- the request and answer;
- actor identity for that session and the mapping from the session ID;
- Running state during work;
- no unrelated resources or identifiers.

### 4. Prove suspension

After the response closes, record:

- the same actor reaching Suspended;
- a sanitized snapshot reference or snapshot existence receipt;
- worker capacity becoming available again.

Do not describe suspension as deletion. The saved state is the point of the demonstration.

### 5. Prove restoration

Send a second request with `demo-session-01`: "What marker did I ask you to remember?" Record the correct marker and the same logical actor returning to Running before it suspends again. The actor and snapshot transition, rather than the model's answer alone, proves restoration.

### 6. Prove separation

Create `demo-session-02` and ask for the remembered marker. The new session must not return `ORANGE-FALCON-17`. Record the separate actor identity.

This checks session separation in this workflow. It does not prove complete tenant isolation. Data, identity, tools and external services need their own boundaries.

## Receipt to retain

Store a sanitized text receipt beside the finished capture containing:

- date and UTC timestamps;
- source revision;
- kagent and Agent Substrate versions;
- CRD served and storage versions;
- exact synthetic resource names;
- Ready, Running and Suspended status excerpts;
- same-session continuity result;
- separate-session result;
- limitations and any failed steps;
- SHA-256 values for the raw capture and final master.

## Stop conditions

Stop the recording and discard the affected clip if any of these appear:

- employer or customer name;
- internal cluster, namespace, subscription or project identifier;
- private repository or endpoint;
- personal access token, API key, cookie or kubeconfig content;
- real prompt, incident, ticket or operational data;
- an unverified state presented as successful.

## Publication boundary

The finished short may describe David's enterprise kagent experience and show this sanitized reconstruction. It must not claim that the public environment is the confidential production fleet, that suspension deletes retained data, or that current performance has been measured until a fresh receipt proves it.
