Raw portable entrypoint: [SKILL.md.txt](downloads/skill/SKILL.md.txt).


# MkDocs project documentation

Deliver a usable MkDocs project, not just a README describing one. Preserve the
user's requested subject and scope; documentation work does not authorise
deployment, credential changes or execution of the documented procedures.

## Choose the source of truth

- Inspect existing `mkdocs.yml`, documentation sources and local instructions
  before scaffolding. Reuse the site's theme, dependency management and build
  workflow unless the requested change requires something different.
- For README-to-site conversions, preserve the canonical source and either use
  a checked synchronization mechanism or explicitly choose which copy owns
  future edits. Update both generated content and its source when required.
- Keep observed results, proposed configuration, template validation and live
  target-system proof distinct. A successful documentation build proves no
  Kubernetes, authentication, delivery or agent behaviour.

## Build the documentation

For a new standalone site, adapt [assets/starter/mkdocs.yml](downloads/skill/assets/starter/mkdocs.yml),
[requirements.txt](downloads/skill/assets/starter/requirements.txt) and
[docs/index.md](downloads/skill/assets/starter/docs/index.md.txt). Change the site title and content to
the actual project. The starter uses MkDocs 1.6.1 and its built-in theme; check
the existing project or official release information before choosing a different
version. Do not replace an established theme or add Material/plugins just to
convert the document format.

Use task-based navigation appropriate to the content. A technical handoff often
needs an overview, prerequisites, the shortest setup path, examples, validation,
rollback and evidence limits. Create only the pages the task benefits from.

Preserve copyable commands and actual YAML/JSON files alongside prose. Use local
relative links for site pages and bundled files so the handoff can be moved.
Rewrite repository-relative links that would escape `docs_dir`, include the
referenced public file, or link explicitly to its authoritative external source.
Do not label an HTML-rendered Markdown page as a raw downloadable skill file.

Keep documentation assets self-contained where practical. Standard MkDocs does
not render Mermaid fences automatically: use a readable text/SVG diagram or an
explicitly configured renderer with documented dependencies. Preserve an existing
supported Mermaid integration rather than adding a second renderer. For an
offline/local-file deliverable, consider `use_directory_urls: false` and verify
that the result actually works under the intended preview method.

Use explicit placeholders for private environment values. Do not bundle local
credentials, populated workplace values, private receipts, venvs or build output
into a public source handoff. Prefer an explicit public file manifest for any
copy/generation script over copying an entire working directory.

## Verify the result

1. Install the declared dependencies in an isolated environment or use the
   existing project environment. In restricted environments, use its approved
   package source; do not silently assume public package access.
2. Run `python -m mkdocs build --strict` with the intended configuration. Fix
   broken nav, file links and anchors; do not lower validation severity solely
   to make the build pass. If content is generated, check its freshness too.
3. Open the built site or local preview when a browser is available. Check the
   main reading path, code blocks, tables, search and at least one real download.
   If browser review is unavailable, report the narrower build/link evidence.
4. Run the repository's proportionate public-safety checks before authorised
   publication. Do not rerun the documented live operations to validate prose.

In the handoff, give the MkDocs project path, exact build/preview commands,
dependency requirements, source-of-truth rule and observed validation. A local
build or source push is not a hosted website; deploy/publish the generated site
only when the user requests it. If a skill was installed, name its actual
installation path and distinguish that from the portable source copy.

Official references: [MkDocs](https://www.mkdocs.org/),
[configuration](https://www.mkdocs.org/user-guide/configuration/),
[writing docs](https://www.mkdocs.org/user-guide/writing-your-docs/).
