#!/usr/bin/env python3
"""Bounded Git/test/draft-PR evidence gate for one Buzz SDLC delivery.

This deliberately verifies an already-created draft PR. It never pushes,
creates commits, changes branches, deploys, or merges. A separate, explicitly
approved publisher may create the draft PR; this gate makes its evidence
machine-readable and keeps merge authority with a human.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any


def run(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "command failed"
        raise RuntimeError(f"{' '.join(args[:3])}: {detail}")
    # unittest and many test runners report successful summaries on stderr;
    # retain both streams in the SHA-bound receipt.
    return (completed.stdout + completed.stderr).strip()


def gate(repo: Path, base: str, pr: str, test_command: str) -> dict[str, Any]:
    root = Path(run(["git", "rev-parse", "--show-toplevel"], repo))
    dirty = run(["git", "status", "--porcelain"], root)
    if dirty:
        raise RuntimeError("delivery gate requires a clean checkout")
    branch = run(["git", "branch", "--show-current"], root)
    if not branch:
        raise RuntimeError("delivery gate refuses detached HEAD")
    run(["git", "merge-base", "--is-ancestor", base, "HEAD"], root)
    sha = run(["git", "rev-parse", "HEAD"], root)
    test_args = shlex.split(test_command)
    if not test_args or any(token in {"|", ";", "&&", "||", ">", "<"} for token in test_args):
        raise RuntimeError("test command must be one direct executable command")
    test_output = run(test_args, root)
    pr_data = json.loads(run(["gh", "pr", "view", pr, "--json", "number,url,isDraft,headRefName,baseRefName,state"], root))
    if pr_data.get("state") != "OPEN" or not pr_data.get("isDraft"):
        raise RuntimeError("delivery gate requires an open draft PR")
    if pr_data.get("headRefName") != branch or pr_data.get("baseRefName") != base:
        raise RuntimeError("draft PR does not match the checked-out branch and base")
    return {
        "schema": "buzz-kagent-sdlc.delivery-gate.v1",
        "git_sha": sha,
        "branch": branch,
        "base": base,
        "test_command": test_args,
        "test_output_tail": test_output[-2000:],
        "draft_pr": {"number": pr_data["number"], "url": pr_data["url"]},
        "ready_for_human_review": True,
        "merge_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="main")
    parser.add_argument("--pr", required=True, help="existing draft PR number or URL")
    parser.add_argument("--test", required=True, dest="test_command", help="one direct test command")
    args = parser.parse_args()
    try:
        print(json.dumps(gate(args.repo.resolve(), args.base, args.pr, args.test_command), indent=2))
    except RuntimeError as exc:
        print(json.dumps({"schema": "buzz-kagent-sdlc.delivery-gate.v1", "passed": False, "error": str(exc), "merge_eligible": False}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
