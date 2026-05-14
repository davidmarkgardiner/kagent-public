from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Settings


@dataclass(frozen=True)
class PullRequestResult:
    mode: str
    branch: str
    pr_url: str
    changed_file: str
    summary: str


class PullRequestService:
    def __init__(self, repo_root: Path, settings: Settings):
        self.repo_root = repo_root
        self.settings = settings

    def open_update_pr(
        self,
        question: str,
        source_path: str,
        reason: str,
        simulate: bool = False,
    ) -> PullRequestResult:
        branch = f"mil-128/kagent-kb-update-{int(time.time())}"
        safe_source = source_path or "docs/platform-kb/aks/shared-aks-resources.md"
        target = (self.repo_root / safe_source).resolve()
        if not str(target).startswith(str(self.repo_root.resolve())):
            raise ValueError("source_path must stay inside the knowledge repo")

        if simulate:
            return self._simulate(branch, safe_source, question, reason)

        if not target.exists():
            raise FileNotFoundError(f"source document not found: {safe_source}")

        self._run(["git", "checkout", "-B", branch], cwd=self.repo_root)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n\n## K-Agent feedback update\n\n"
                f"- Question: {question}\n"
                f"- Feedback: {reason}\n"
                "- Action: Platform engineer review required; update this guidance "
                "with the corrected operational detail.\n"
            )
        self._run(["git", "add", safe_source], cwd=self.repo_root)
        self._run(
            ["git", "commit", "-m", "MIL-128 Capture stale knowledge feedback"],
            cwd=self.repo_root,
        )
        self._run(["git", "push", "-u", "origin", branch], cwd=self.repo_root)
        body = (
            "Refs MIL-128\n\n"
            "K-Agent Knowledge UI flagged this source as stale or incorrect.\n\n"
            f"- Question: {question}\n"
            f"- Feedback: {reason}\n"
            f"- Source: {safe_source}\n"
        )
        pr_url = self._run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                self.settings.github_repo,
                "--base",
                self.settings.github_base_branch,
                "--head",
                branch,
                "--title",
                "MIL-128 Update stale K-Agent knowledge",
                "--body",
                body,
                "--label",
                "symphony",
            ],
            cwd=self.repo_root,
        )
        return PullRequestResult(
            mode="real",
            branch=branch,
            pr_url=pr_url,
            changed_file=safe_source,
            summary="Opened GitHub PR with gh.",
        )

    def _simulate(
        self, branch: str, source_path: str, question: str, reason: str
    ) -> PullRequestResult:
        self.settings.evidence_dir.mkdir(parents=True, exist_ok=True)
        result = PullRequestResult(
            mode="simulated",
            branch=branch,
            pr_url=f"https://github.com/{self.settings.github_repo}/pull/simulated-mil-128",
            changed_file=source_path,
            summary="Simulated stale-doc PR creation for smoke test.",
        )
        payload = {
            **asdict(result),
            "question": question,
            "reason": reason,
        }
        (self.settings.evidence_dir / "simulated-stale-doc-pr.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    @staticmethod
    def _run(command: list[str], cwd: Path) -> str:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"command failed: {' '.join(command)}\n"
                f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
            )
        return result.stdout.strip()

