import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bmad_orch.config.schema import validate_config
from bmad_orch.exceptions import GitError
from bmad_orch.git import GitClient, GitStatus


@pytest.mark.asyncio
async def test_git_client_init_non_repo():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"not a git repository")
        mock_exec.return_value = mock_process
        
        with pytest.raises(GitError, match="not a git repository"):
            await GitClient.create()

@pytest.mark.asyncio
async def test_git_client_lock_retry():
    with patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        
        # Mock rev-parse and identity checks
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"ok\n", b"")
        
        # Mock lock contention failure then success
        mock_lock = AsyncMock()
        mock_lock.returncode = 1
        mock_lock.communicate.return_value = (b"", b"another git process seems to be running... index.lock")
        
        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_lock, mock_ok]
        
        client = await GitClient.create()
        await client.add(["test.txt"])
        
        assert mock_exec.call_count == 5
        assert mock_sleep.call_count == 1

@pytest.mark.asyncio
async def test_git_client_timeout():
    with patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):

        mock_process = AsyncMock()
        # kill() is synchronous on real Process, so use MagicMock to avoid
        # "coroutine never awaited" warning
        mock_process.kill = MagicMock()
        mock_exec.return_value = mock_process

        client = GitClient(Path.cwd())
        with pytest.raises(GitError, match="timed out"):
            await client._run_git("status")

        mock_process.kill.assert_called_once()

@pytest.mark.asyncio
async def test_git_identity_fallback():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock rev-parse ok
        mock_is_repo = AsyncMock()
        mock_is_repo.returncode = 0
        mock_is_repo.communicate.return_value = (b"true\n", b"")
        
        # Mock identity check fails
        mock_fail = AsyncMock()
        mock_fail.returncode = 1
        mock_fail.communicate.return_value = (b"", b"")
        
        mock_exec.side_effect = [mock_is_repo, mock_fail, mock_fail]
        
        client = await GitClient.create()
        assert client._env["GIT_AUTHOR_NAME"] == "bmad-orch[bot]"
        assert client._env["GIT_COMMITTER_NAME"] == "bmad-orch[bot]"


@pytest.mark.asyncio
async def test_git_commit_nothing_to_commit_noop():
    """AC9: Gracefully no-op when there are no staged changes."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock rev-parse and identity checks for create()
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        # Mock status showing clean tree (no non-comment lines)
        mock_status = AsyncMock()
        mock_status.returncode = 0
        mock_status.communicate.return_value = (b"# branch.head main\n", b"")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_status]

        client = await GitClient.create()
        # Should not raise — just skip
        await client.commit("test message")

        # git commit should never have been called (only rev-parse, config x2, status)
        assert mock_exec.call_count == 4


@pytest.mark.asyncio
async def test_git_push_failure_raises_git_error():
    """AC8: Push failure raises GitError with clear message."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        mock_push_fail = AsyncMock()
        mock_push_fail.returncode = 1
        mock_push_fail.communicate.return_value = (b"", b"fatal: Authentication failed")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_push_fail]

        client = await GitClient.create()
        with pytest.raises(GitError, match="Failed to push"):
            await client.push()


@pytest.mark.asyncio
async def test_git_add_never_uses_force():
    """AC11: add() strictly respects .gitignore by never using --force."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_ok]

        client = await GitClient.create()
        await client.add(["file1.txt", "file2.txt"])

        # Inspect the add() call args (4th call, index 3)
        add_call = mock_exec.call_args_list[3]
        git_args = add_call[0]  # positional args to create_subprocess_exec
        assert git_args == ("git", "add", "file1.txt", "file2.txt")
        assert "--force" not in git_args


@pytest.mark.asyncio
async def test_git_add_empty_paths_noop():
    """add() with empty list does nothing."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok]

        client = await GitClient.create()
        await client.add([])
        # Only 3 calls: rev-parse + 2 identity checks, no add call
        assert mock_exec.call_count == 3


@pytest.mark.asyncio
async def test_git_status_parsing():
    """AC1: status() returns parsed GitStatus dataclass."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        porcelain_output = (
            b"# branch.head main\n"
            b"# branch.ab +2 -1\n"
            b"1 M. N... 100644 100644 abc def src/file.py\n"
        )
        mock_status = AsyncMock()
        mock_status.returncode = 0
        mock_status.communicate.return_value = (porcelain_output, b"")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_status]

        client = await GitClient.create()
        result = await client.status()

        assert isinstance(result, GitStatus)
        assert result.branch == "main"
        assert result.ahead == 2
        assert result.behind == 1
        assert result.is_clean is False


@pytest.mark.asyncio
async def test_git_push_timeout_uses_60s():
    """AC14: Push uses 60s timeout, not the default 30s."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_ok = AsyncMock()
        mock_ok.returncode = 0
        mock_ok.communicate.return_value = (b"true\n", b"")

        mock_exec.side_effect = [mock_ok, mock_ok, mock_ok, mock_ok]

        client = await GitClient.create()
        # Patch wait_for to capture the timeout value
        with patch("asyncio.wait_for", wraps=asyncio.wait_for) as mock_wait:
            await client.push()
            # The push call's wait_for should use timeout=60.0
            push_wait_call = mock_wait.call_args
            assert push_wait_call[1]["timeout"] == 60.0, (
                f"Expected push timeout 60.0, got {push_wait_call[1].get('timeout')}"
            )


@pytest.mark.asyncio
async def test_commit_at_never_skips_commit():
    """AC15: commit_at='never' skips all commit operations."""
    from bmad_orch.engine.cycle import CycleExecutor

    cfg_data = {
        "providers": {1: {"name": "mock", "cli": "mock", "model": "m1"}},
        "cycles": {"c1": {"steps": [{"skill": "s1", "provider": 1, "type": "validation", "prompt": "p"}]}},
        "git": {"enabled": True, "commit_at": "never", "push_at": "never"},
        "pauses": {"between_steps": 0, "between_cycles": 0, "between_cycle_types": 0, "between_workflows": 0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config = validate_config(cfg_data)

    mock_git = AsyncMock(spec=GitClient)
    executor = CycleExecutor(
        emitter=MagicMock(),
        state_manager=MagicMock(),
        prompt_resolver=MagicMock(),
        config=config,
        state_path=Path("/dev/null"),
        git_client=mock_git,
    )

    # commit_at="never" should not match "step" or "cycle"
    await executor._handle_git_commit("step", "test_step", True)
    await executor._handle_git_commit("cycle", "test_cycle", True)

    mock_git.add.assert_not_called()
    mock_git.commit.assert_not_called()


@pytest.mark.asyncio
async def test_push_at_never_skips_push():
    """AC15: push_at='never' skips all push operations."""
    from bmad_orch.engine.cycle import CycleExecutor

    cfg_data = {
        "providers": {1: {"name": "mock", "cli": "mock", "model": "m1"}},
        "cycles": {"c1": {"steps": [{"skill": "s1", "provider": 1, "type": "validation", "prompt": "p"}]}},
        "git": {"enabled": True, "commit_at": "cycle", "push_at": "never"},
        "pauses": {"between_steps": 0, "between_cycles": 0, "between_cycle_types": 0, "between_workflows": 0},
        "error_handling": {"retry_transient": True, "max_retries": 3, "retry_delay": 10},
    }
    config = validate_config(cfg_data)

    mock_git = AsyncMock(spec=GitClient)
    executor = CycleExecutor(
        emitter=MagicMock(),
        state_manager=MagicMock(),
        prompt_resolver=MagicMock(),
        config=config,
        state_path=Path("/dev/null"),
        git_client=mock_git,
    )

    # push_at="never" should not match "cycle" or "end"
    await executor._handle_git_push("cycle")
    await executor._handle_git_push("end")

    mock_git.push.assert_not_called()
