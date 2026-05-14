from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Settings


class RepositorySyncError(RuntimeError):
    pass


def _run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RepositorySyncError(
            f"command failed: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


class KnowledgeRepo:
    def __init__(self, settings: Settings):
        self.settings = settings

    def sync(self) -> Path:
        if self.settings.kb_local_path:
            path = Path(self.settings.kb_local_path).expanduser().resolve()
            if not path.exists():
                raise RepositorySyncError(f"KB_LOCAL_PATH does not exist: {path}")
            return path

        path = self.settings.kb_clone_dir
        if (path / ".git").exists():
            _run(["git", "fetch", "origin", self.settings.kb_repo_ref], cwd=path)
            _run(["git", "checkout", self.settings.kb_repo_ref], cwd=path)
            _run(
                ["git", "pull", "--ff-only", "origin", self.settings.kb_repo_ref],
                cwd=path,
            )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            _run(
                [
                    "git",
                    "clone",
                    "--branch",
                    self.settings.kb_repo_ref,
                    self.settings.kb_repo_url,
                    str(path),
                ]
            )
        return path

