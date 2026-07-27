# kagent work bundles

This directory is the canonical source for the self-contained operator bundles
in the `kagent-public` repository. It is mirrored at repository root in
[`davidmarkgardiner/kagent-work-bundles`](https://github.com/davidmarkgardiner/kagent-work-bundles)
so a work environment can clone only the bundles it needs.

## Use at work

Clone the sister repository, then select the required bundle. Each bundle owns
its own README, manifests, prerequisites, validation, smoke tests, and safety
notes. Do not assume one bundle's credentials, namespaces, or runtime components
are prerequisites for another.

## Source and synchronization

`kagent-public` remains the source of truth. Make reviewed bundle changes here
first, merge them to `main`, then mirror the subtree:

```bash
git remote add work-bundles https://github.com/davidmarkgardiner/kagent-work-bundles.git
scripts/sync-work-bundles-repo.sh
```

The sync script publishes the committed `work-agent-bundles/` subtree to the
sister repository's `main` branch. Do not make independent production edits in
the sister repository: they will be overwritten by the next source sync.
