# Private GitLab Evaluation Pattern (Air-Gapped)

For a copy-ready stakeholder summary, see
[`TEAMS-TLDR.md`](TEAMS-TLDR.md).

This is a small, repeatable demonstration for assessing code submissions without
exposing them to people who are not on the assessment panel. It is designed for
an air-gapped, self-managed GitLab instance; it makes no calls to SaaS services
and contains no real endpoint, token, candidate, or model details.

It deliberately does **not** claim that an agent is “tamper-proof”. A pipeline
result is trustworthy only to the extent that the evaluator project, its
protected configuration, runner, identity, inputs, and audit trail are
protected. This design makes those boundaries explicit.

## What the demo creates

Run [`bootstrap-airgapped-demo.sh`](bootstrap-airgapped-demo.sh) from a trusted
administrator workstation to create these two **private** projects in an
existing restricted GitLab group:

```
{{GITLAB_NAMESPACE}}/submission-private-demo
  candidate/change ── private MR ──> main
          │
          │ immutable commit SHA and a read-only project token
          ▼
{{GITLAB_NAMESPACE}}/evaluation-authority-demo
  protected main → trusted CI evaluation job → retained evidence artifact
```

The submission project is the private working area. The evaluation authority is
the separately administered control plane: candidates must not be members with
Maintainer access and must not be able to change its `main` branch, runners, or
CI variables. The script creates a harmless sample private MR and a central
evaluation pipeline definition. It does **not** create an MR to any shared or
public upstream project.

## Before running

1. Create a private GitLab group that contains only the assessment panel and
   evaluation-service administrators. Do not use an `internal` project: internal
   visibility is readable by every authenticated user on many self-managed
   GitLab installations.
2. Install `glab` on a workstation that can reach the air-gapped GitLab server
   and authenticate it to that host.
3. Use an owner-level operator account for the first bootstrap. The evaluator
   runner must be a protected, trusted runner; never use an untrusted shared
   runner for submitted code.

The bootstrap intentionally refuses to default to `gitlab.com`:

```sh
export GITLAB_HOST=gitlab.{{YOUR_INTERNAL_DOMAIN}}
export GITLAB_NAMESPACE={{RESTRICTED_GROUP_PATH}}
./demos/gitlab-private-evaluation/bootstrap-airgapped-demo.sh
```

The projects and the local temporary clone directory are disposable. The script
prints the project URLs and stops before running an evaluation because the
read-only token is a secret that must be created under your organisation’s
process.

## Complete the evaluation proof

Create a **project access token** in `submission-private-demo` with the minimum
repository-read scope needed by your GitLab version. Store it only as the
masked, protected `EVALUATOR_READ_TOKEN` CI variable in
`evaluation-authority-demo`:

```sh
export EVALUATOR_READ_TOKEN='{{TOKEN_CREATED_IN_GITLAB}}'
glab variable set EVALUATOR_READ_TOKEN "$EVALUATOR_READ_TOKEN" \
  --masked --protected \
  --repo "$GITLAB_HOST/$GITLAB_NAMESPACE/evaluation-authority-demo"
unset EVALUATOR_READ_TOKEN
```

Then obtain the submission project ID and private-MR IID, and start the
authority pipeline. The authority job resolves the MR head SHA through the
GitLab API itself; it does not trust a caller-supplied commit SHA:

```sh
SUBMISSION_PROJECT_ID="$(glab api --hostname "$GITLAB_HOST" \
  "projects/$GITLAB_NAMESPACE%2Fsubmission-private-demo" --jq .id)"
SUBMISSION_MR_IID=1

glab ci run --branch main \
  --repo "$GITLAB_HOST/$GITLAB_NAMESPACE/evaluation-authority-demo" \
  --variables-env "SUBMISSION_PROJECT_ID:$SUBMISSION_PROJECT_ID" \
  --variables-env "SUBMISSION_MR_IID:$SUBMISSION_MR_IID"
```

The demo job resolves and downloads the submission only by the private MR's
immutable head SHA, checks a
small policy example, and publishes `evaluation-result.json` as an artifact. It
is deliberately a deterministic stand-in for the valuation agent: replace only
the `evaluate-submission` job body with the approved internal agent invocation.
Do not let submission-controlled `.gitlab-ci.yml`, prompts, or artifacts decide
what the evaluator executes.

## Validate the boundary

Use a non-panel test account for the following checks and retain screenshots or
audit evidence with the assessment record:

| Check | Expected result |
| --- | --- |
| Open either project or private MR URL | `404`/access denied; no title, diff, commits, jobs, or artifacts visible. |
| Search GitLab for the project/MR | No result. |
| Clone the submission repository | Access denied. |
| Open the evaluation pipeline/artifact | Access denied. |
| Panel member opens the private MR | Visible, reviewable, and auditable. |
| Candidate tries to modify the authority `main` branch or protected variable | Rejected. |
| Authority pipeline receives an MR not belonging to the submission project | The evaluator must reject it before any model/tool call. |

The last check is essential when you replace the demo job: resolve and compare
the source project and MR through the GitLab API, restrict input size and
file types, and treat repository content as untrusted prompt input.

## Promotion and retention

There are two valid endings; choose one before onboarding candidates:

- **Disclosure permitted:** after an approval decision, an authorised release
  bot creates a clean MR to the shared repository. This is the first point at
  which the code becomes broadly visible.
- **Disclosure prohibited:** do not create an upstream MR. A named authorised
  maintainer applies the accepted, recorded commit into the destination under
  its normal change controls, or retains it solely in the restricted project.

Do not use MR deletion as the confidentiality control. Git history, pipeline
logs, artifacts, fork relations, emails, caches, and audit events can outlive
an MR. Set artifact expiry and project retention deliberately, export the final
evidence where policy requires it, and use the organisation’s approved purge
process.

## Security ownership checklist

- GitLab administrators: private group/project policy, audit-event retention,
  backup and deletion policy.
- Assessment lead: group membership and reviewer separation of duties.
- Evaluation-platform owner: protected authority branch, masked variables,
  pinned internal model/tool image, and protected runner.
- Candidate: access only to their own private submission project; no evaluator
  project membership or secrets.

The GitLab-specific rationale is documented in the official GitLab guidance:
[confidential issues do not make MRs confidential](https://docs.gitlab.com/user/project/merge_requests/confidential/);
sensitive work stays in a private fork/project until it is ready for disclosure.
Mirror that page into the air-gapped documentation service if external links are
not reachable from operator workstations.
