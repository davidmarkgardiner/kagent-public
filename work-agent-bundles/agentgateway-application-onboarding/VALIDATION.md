# Portable bundle validation

Checked on 30 October 2026.

- Copied this folder to an operating-system temporary directory. Every relative
  Markdown link resolved to an existing file inside the copied folder.
- All 16 YAML files parsed with PyYAML. The 13 configuration example files
  contain 18 Kubernetes resource examples. The other three YAML files are
  intake/example data contracts, not Kubernetes resources.
- The 11 copied Microsoft examples match their source text. File 05 changes
  only the documented model gateway path from `/azure/v1` to `/team/v1`.
- The complete bundle passes the normal public-safe scan. The new example
  directory, compatibility note, walkthrough, and root README also pass strict
  scans. Strict scanning of the entire inherited bundle flags seven existing
  prose or illustrative access-token lines. Those lines contain no credentials.
- Gitleaks reports no leaks. Detect-secrets reports two unverified Secret
  Keyword findings in file 05. Both are public Secret name/key references,
  `model-gateway-auth` and `api-key`, rather than credential values. No scan
  suppression was added.
- A separate read-only review found no substantive portability or configuration
  issue. Git whitespace checks pass.

These checks establish folder portability, YAML parsing, and reviewed public
content. They do not establish installed CRD compatibility, API-server
admission, Entra provisioning, backend reachability, token refresh, or runtime
allow/deny behavior. Use the [acceptance checklist](evidence/ACCEPTANCE-CHECKLIST.md)
for target-environment evidence.
