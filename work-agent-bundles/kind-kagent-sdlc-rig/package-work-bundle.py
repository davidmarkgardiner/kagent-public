#!/usr/bin/env python3
"""Make one deterministic, secret-free transfer archive and checksum."""

import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parent
NAME = "kind-kagent-sdlc-rig"
FILES = (
    "00-foundation.yaml", "10-a2a-agents.yaml", "20-delivery-workers.yaml",
    "30-board-cronjob.yaml", "BOARD-POLLING-PRESENTATION.html", "PLAN.md",
    "README.md", "REVIEW-TASKS.md", "WORK-CLUSTER-RUNBOOK.md", "board_poller.py",
    "WORK-AGENT-START-PROMPT.md", "LIVE-DEMO-RUNBOOK.md", "DEMO-ISSUE-TEMPLATE.md",
    "HOMELAB-REFERENCE.md", "CI-RUNNER-SETUP.md", "ci-runner-values.example.yaml",
    "evidence/RUN-2026-10-01.md", "images.lock.tsv", "package-work-bundle.py", "preflight.sh",
    "render-gitlab-mcp.py", "render-work-bundle.py", "test_board_poller.py",
    "test_render_work_bundle.py", "work-profile.example.json",
    "evidence/2026-09-27-board-polling.md", "evidence/2026-09-27-live-run.md",
    "evidence/2026-09-27-unattended-lease-canary.md",
    "evidence/RUN-2026-09-27.md", "evidence/2026-09-27-review-followup.md",
    "evidence/PRESENTATION-CHECKS-2026-10-01.md",
    "tools/PROVENANCE.md", "tools/kagent-a2a-invoke.sh",
    "vendor/PROVENANCE.md", "vendor/gitlab-delivery-mcp.yaml",
    "review-repros/README.md", "review-repros/repro_ci_loop.py",
    "review-repros/repro_findings.py",
)


def add_bytes(archive, name, data, executable=False):
    info = tarfile.TarInfo(f"{NAME}/{name}")
    info.size = len(data)
    info.mode = 0o755 if executable else 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    archive.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = [ROOT / name for name in FILES]
    missing = [str(path) for path in paths if not path.is_file() or path.is_symlink()]
    if missing:
        parser.error("missing or symlinked bundle file: " + ", ".join(missing))
    files = {name: path.read_bytes() for name, path in zip(FILES, paths)}
    manifest = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(files.items())
    ).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name, data in sorted(files.items()):
                    add_bytes(archive, name, data, name.endswith(".sh") or name == "package-work-bundle.py")
                add_bytes(archive, "MANIFEST.sha256", manifest)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    sidecar = args.output.with_name(args.output.name + ".sha256")
    sidecar.write_text(f"{digest}  {args.output.name}\n")
    print(f"{args.output} sha256={digest} files={len(files) + 1}")


if __name__ == "__main__":
    main()
