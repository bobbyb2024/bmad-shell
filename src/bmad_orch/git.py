import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import structlog

from bmad_orch.exceptions import GitError

logger = structlog.get_logger(__name__)

__all__ = ["GitClient", "GitStatus"]

@dataclass(frozen=True)
class GitStatus:
    is_clean: bool
    branch: str | None
    ahead: int
    behind: int

class GitClient:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self._env = os.environ.copy()
        self._env.update({
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EDITOR": "true",
            "GIT_ASKPASS": "echo",
            "SSH_ASKPASS": "echo",
            "LANG": "C",
        })

    @classmethod
    async def create(cls, repo_path: Path | None = None) -> Self:
        path = repo_path or Path.cwd()
        client = cls(path)
        # Verify it's a git repo
        code, _, stderr = await client._run_git("rev-parse", "--is-inside-work-tree")
        if code != 0:
            raise GitError(f"Working directory '{path}' is not a git repository: {stderr.strip()}")
        
        # Check for global git config and provide fallbacks if missing
        await client._ensure_identity()
        return client

    async def _ensure_identity(self) -> None:
        # Check user.name
        code, _, _ = await self._run_git("config", "--get", "user.name")
        has_name = code == 0
        
        # Check user.email
        code, _, _ = await self._run_git("config", "--get", "user.email")
        has_email = code == 0

        if not has_name or not has_email:
            logger.warning("Git identity not fully configured, providing fallbacks", 
                           has_name=has_name, has_email=has_email)
            self._env.update({
                "GIT_AUTHOR_NAME": "bmad-orch[bot]",
                "GIT_AUTHOR_EMAIL": "bmad-orch@localhost",
                "GIT_COMMITTER_NAME": "bmad-orch[bot]",
                "GIT_COMMITTER_EMAIL": "bmad-orch@localhost",
            })

    async def _run_git(self, *args: str, timeout: float = 30.0, max_retries: int = 10) -> tuple[int, str, str]:
        attempt = 0
        while attempt < max_retries:
            process = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=self.repo_path,
                env=self._env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
                stdout = stdout_bytes.decode()
                stderr = stderr_bytes.decode()
                
                if process.returncode != 0:
                    # Check for lock contention
                    if "index.lock" in stderr or "HEAD.lock" in stderr:
                        attempt += 1
                        if attempt < max_retries:
                            logger.warning("Git lock detected, retrying...", attempt=attempt, max_retries=max_retries)
                            await asyncio.sleep(1.0)
                            continue
                        msg = (
                            f"Git operation 'git {' '.join(args)}' failed after "
                            f"{max_retries} retries: {stderr.strip()}"
                        )
                        raise GitError(msg)
                
                return process.returncode or 0, stdout, stderr
            except TimeoutError as e:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()
                msg = f"Git operation 'git {' '.join(args)}' timed out after {timeout}s"
                raise GitError(msg) from e
            except Exception as e:
                if not isinstance(e, GitError):
                    raise GitError(f"Git operation 'git {' '.join(args)}' failed: {e}") from e
                raise
        
        # Should not reach here due to return/raise above
        return -1, "", "Unexpected error in _run_git loop"

    async def status(self) -> GitStatus:
        # Using porcelain=v2 for stable parsing
        code, stdout, stderr = await self._run_git("status", "--porcelain=v2", "--branch")
        if code != 0:
            raise GitError(f"Failed to get git status: {stderr}")

        is_clean = True
        branch = None
        ahead = 0
        behind = 0

        for line in stdout.splitlines():
            if line.startswith("# branch.head "):
                branch = line.split(" ")[2]
            elif line.startswith("# branch.ab "):
                parts = line.split(" ")
                ahead = int(parts[2].replace("+", ""))
                behind = int(parts[3].replace("-", ""))
            elif not line.startswith("#"):
                is_clean = False

        return GitStatus(is_clean=is_clean, branch=branch, ahead=ahead, behind=behind)

    async def add(self, paths: list[str]) -> None:
        if not paths:
            return
        # Never use --force to respect .gitignore
        code, _, stderr = await self._run_git("add", *paths)
        if code != 0:
            raise GitError(f"Failed to add paths {paths}: {stderr}")

    async def commit(self, message: str) -> None:
        # Check if there's anything to commit
        status = await self.status()
        if status.is_clean:
            logger.info("Nothing to commit, skipping")
            return

        code, _, stderr = await self._run_git("commit", "-m", message)
        if code != 0:
            # Handle the case where there are unstaged changes but nothing staged
            if "no changes added to commit" in stderr:
                logger.info("No staged changes to commit, skipping")
                return
            raise GitError(f"Failed to commit: {stderr}")

    async def push(self, remote: str = "origin", branch: str | None = None) -> None:
        args = ["push", remote]
        if branch:
            args.append(branch)
        
        # 60s timeout for push as per AC
        code, _, stderr = await self._run_git(*args, timeout=60.0)
        if code != 0:
            raise GitError(f"Failed to push to {remote}: {stderr}")

    async def fetch(self, remote: str = "origin") -> None:
        code, _, stderr = await self._run_git("fetch", remote)
        if code != 0:
            raise GitError(f"Failed to fetch from {remote}: {stderr}")
