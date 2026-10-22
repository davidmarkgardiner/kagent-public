# Source security audit

The authoritative portable work-agent bundle is
[work-agent-bundles/source-security-audit](../../work-agent-bundles/source-security-audit/README.md).
It combines the pinned Cloudflare security-audit skill with real child-invocation
receipts and source-only report checks. A delegation-capable coding runner does
the source review. Its optional no-tool kagent Agent reviews supplied evidence;
it does not perform repository scans.

Keep the Agent manifest in the bundle as the single source of truth.
