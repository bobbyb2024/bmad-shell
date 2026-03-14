import asyncio
from unittest.mock import patch

import pytest

from bmad_orch.exceptions import ProviderCrashError, ProviderError, ProviderTimeoutError
from bmad_orch.providers.claude import ClaudeAdapter
from bmad_orch.types import OutputChunk


def test_detect_success():
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b"claude 0.1.0\n"
            adapter = ClaudeAdapter()
            assert adapter.detect() is True
            assert adapter._version == "claude 0.1.0"
            # Verify it used the absolute path
            mock_exec.assert_called_with(["/usr/local/bin/claude", "--version"], stderr=-2) # -2 is subprocess.STDOUT

def test_detect_failure():
    with patch("shutil.which", return_value=None):
        adapter = ClaudeAdapter()
        assert adapter.detect() is False

def test_list_models_fallback():
    adapter = ClaudeAdapter()
    import subprocess
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")):
            models = adapter.list_models()
            assert len(models) == 2
            assert models[0]["id"] == "claude-3-5-sonnet-latest"

def test_list_models_success():
    adapter = ClaudeAdapter()
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b'[{"id": "model-1", "name": "Model 1"}]'
            models = adapter.list_models()
            assert len(models) == 1
            assert models[0]["id"] == "model-1"

@pytest.mark.asyncio
async def test_execute_auth_propagation():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        # We need to mock spawn_pty_process
        mock_chunks = [OutputChunk(content="Hello", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            # Check env contains the API key and preserves system env
            assert kwargs["env"]["ANTHROPIC_API_KEY"] == "test-key"
            assert "PATH" in kwargs["env"]
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            chunks = []
            async for chunk in adapter.execute("test prompt"):
                chunks.append(chunk)
            
            assert len(chunks) == 1
            assert chunks[0].content == "Hello"
            assert "execution_id" in chunks[0].metadata

@pytest.mark.asyncio
async def test_execute_defensive_parsing_html():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        mock_chunks = [OutputChunk(content="<html><body>Error</body></html>", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match="Corrupted/HTML Provider Output detected."):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_defensive_parsing_binary():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        mock_chunks = [OutputChunk(content="Some data \x00 corrupted", timestamp=1.0)]
        async def mock_spawn(*args, **kwargs):
            for c in mock_chunks:
                yield c

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderError, match=r"Corrupted/HTML Provider Output \(binary detected\)."):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_grace_period_propagation():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {
        "ANTHROPIC_API_KEY": "test-key",
        "CLAUDE_TERMINATION_GRACE_PERIOD": "5.5"
    }, clear=False):
        async def mock_spawn(*args, **kwargs):
            assert kwargs["grace_period"] == 5.5
            yield OutputChunk(content="Ok", timestamp=1.0)

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            async for _ in adapter.execute("test prompt"):
                pass

@pytest.mark.asyncio
async def test_execute_crash_with_version():
    adapter = ClaudeAdapter()
    adapter._version = "claude 0.1.0"
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderCrashError("Process failed with exit code 1")
            yield # dummy

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderCrashError, match="claude 0.1.0"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_timeout_with_version():
    adapter = ClaudeAdapter()
    adapter._version = "claude 0.1.0"
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            raise ProviderTimeoutError("Process timed out after 30s")
            yield # dummy

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(ProviderTimeoutError, match="claude 0.1.0"):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_cancellation():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        async def mock_spawn(*args, **kwargs):
            yield OutputChunk(content="partial", timestamp=1.0)
            raise asyncio.CancelledError()

        with patch("bmad_orch.providers.claude.spawn_pty_process", side_effect=mock_spawn):
            with pytest.raises(asyncio.CancelledError):
                async for _ in adapter.execute("test prompt"):
                    pass

@pytest.mark.asyncio
async def test_execute_no_api_key():
    adapter = ClaudeAdapter()
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY environment variable is mandatory"):
            async for _ in adapter.execute("test prompt"):
                pass
