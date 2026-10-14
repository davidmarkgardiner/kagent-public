# Handoff checks, 14 October 2026

The demonstration clusters had already been deleted. No cluster was created,
queried or smoke-tested while preparing this bank handoff update.

Local checks completed:

- SHA-256 and size verification of all 11 transferred prerequisites.
- Offline preparation in a fresh directory with Git, Go, Helm, curl, wget
  and gh replaced by commands that fail if invoked. Preparation succeeded;
  a wrong-size prerequisite was rejected before installing source/helpers.
- Both Linux AMD64 helpers started with `--help` in a disposable local Docker
  container with `--network none`. This checks startup, not cluster calls.
- Stock chart archives rendered through the image post-renderer. An unmapped
  mutable image was rejected. No rendered manifest was applied.
- Bash syntax, Python syntax and JSON parsing checked. The new template
  discovery parser accepted the previously saved AKS API inventory.
- Relative documentation links and public-safety scan checked before upload.

`smoke-test.sh` is a new orchestration wrapper for the bank agent to execute.
It has not been run on any live cluster. Existing lab evidence and benchmarks
are historical receipts from the earlier deployment; they are retained
without substitution. Bank installation, disconnected delivery, registry
credentials, real-model chat and fresh-node lifecycle proof remain pending.
