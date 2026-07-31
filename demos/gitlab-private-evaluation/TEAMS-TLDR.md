# Teams TL;DR — Private GitLab Code Evaluation

We have a practical GitLab pattern for evaluating sensitive code submissions
without exposing them across the wider organisation.

- Each submission stays in its own **private** GitLab project with a private MR.
- A separate, restricted **evaluation-authority** project owns the protected
  pipeline, runner, token, and evidence artifact.
- The evaluator resolves the private MR through GitLab and evaluates its pinned
  head commit; submission-controlled CI or prompts do not control the evaluator.
- Nothing is merged into a shared/public project until an authorised decision
  says the code may be disclosed.

Important caveat: confidential issues do not make merge requests confidential,
and no agent is inherently “tamper-proof”. The assurance comes from private
project membership, protected evaluator configuration/variables/runners,
least-privilege read access, and retained GitLab audit evidence.

I have added a disposable, air-gapped GitLab demonstration that creates the two
private projects and a sample private MR. It deliberately refuses to run against
GitLab.com; we should execute it only on the work GitLab instance with the
assessment panel’s group and runner controls in place.

Demo guide: `demos/gitlab-private-evaluation/README.md`
