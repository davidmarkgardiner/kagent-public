from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_KB_REPO_URL = "https://github.com/davidmarkgardiner/kagent-public.git"
DEFAULT_TICKET_URL = (
    "https://linear.app/milano2/issue/MIL-128/"
    "poc-k-agent-ui-knowledge-base-driven-assistant-for-aks-platform"
)


@dataclass(frozen=True)
class Settings:
    kb_repo_url: str
    kb_repo_ref: str
    kb_local_path: str | None
    kb_clone_dir: Path
    ticket_url: str
    top_k: int
    min_score: float
    github_repo: str
    github_base_branch: str
    evidence_dir: Path


def load_settings() -> Settings:
    return Settings(
        kb_repo_url=os.getenv("KB_REPO_URL", DEFAULT_KB_REPO_URL),
        kb_repo_ref=os.getenv("KB_REPO_REF", "main"),
        kb_local_path=os.getenv("KB_LOCAL_PATH"),
        kb_clone_dir=Path(
            os.getenv("KB_CLONE_DIR", "/tmp/kagent-knowledge-ui/kagent-public")
        ),
        ticket_url=os.getenv("TICKET_URL", DEFAULT_TICKET_URL),
        top_k=int(os.getenv("TOP_K", "3")),
        min_score=float(os.getenv("MIN_SCORE", "1.6")),
        github_repo=os.getenv("GITHUB_REPO", "davidmarkgardiner/kagent-public"),
        github_base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
        evidence_dir=Path(os.getenv("EVIDENCE_DIR", "docs/poc-evidence")),
    )

