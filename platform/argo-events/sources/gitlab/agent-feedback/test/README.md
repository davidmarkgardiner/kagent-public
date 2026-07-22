# Home-lab Rehydration Test

`mock-gitlab-api.yaml` is a disposable GitLab REST API test double. It accepts
only `test-reader-token` for Issue/thread GET requests and
`test-writer-token` for the response-note POST. It proves the workflow's
separate credential paths without using a real GitLab credential.

The test is intentionally outside the production Kustomization. Delete the
mock, POC resources, secrets, test run-state ConfigMap, and port-forward after
the run.
