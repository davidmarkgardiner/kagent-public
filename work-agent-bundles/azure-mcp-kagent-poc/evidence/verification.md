# Verification, 2026-10-01

| Check | Result |
|---|---|
| Official native Azure MCP 3.0.0-beta.48 MCP initialization | PASS |
| Exact selected tool discovery and read-only annotations | PASS |
| Missing mandatory resource-group argument rejected | PASS |
| Unregistered write tool rejected | PASS |
| Azure operations executed | None |
| Python syntax / shell syntax / YAML parsing | PASS |
| Agent + RemoteMCPServer schema against sibling kagent CRDs | PASS (offline only) |
| Standalone gateway configuration against sibling JSON schema | PASS (offline only) |
| Repository public-safe-scan, strict | PASS |
| First Docker build | PASS; startup failed due to missing ICU |
| ICU fix rebuild and subsequent Docker checks | Interrupted; Docker socket denied after permission change |
| HTTP/gateway runtime, deployed CRDs, kagent A2A, Entra/UAMI/RBAC | NOT VERIFIED |
| Initial Docker fixture cleanup | NOT VERIFIED; run README cleanup command |

The native probe saves only server metadata, tool names, parameter names and check
outcomes in `stdio-receipt.json`. It does not save raw Azure resource data or tokens.
Local schema checks used existing sibling reference clones and do not prove the
schema of any installed cluster or the pinned gateway binary. Gateway runtime names
must still be discovered. No existing repository files were edited for this PoC.
